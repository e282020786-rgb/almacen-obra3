"""Lógica de negocio de Datos Generales del Proyecto.

Toda escritura ocurre dentro de una transacción y deja registro en `auditoria`.
"""
import json
import shutil
import sqlite3
from datetime import date
from pathlib import Path

from app import config
from app.core import validators as v
from app.core.models import Proyecto, Responsable, ROLES, MODALIDADES, TIPOS_ENTIDAD, ESTADOS


class ValidacionError(Exception):
    """errores: dict campo -> mensaje."""

    def __init__(self, errores: dict):
        self.errores = errores
        super().__init__("\n".join(errores.values()))


class ProyectoService:
    MODULO = "DATOS_GENERALES"

    def __init__(self, db, usuario="sistema"):
        self.db = db
        self.usuario = usuario

    # ---------- Consultas ----------
    def listar(self):
        return [Proyecto.desde_fila(f) for f in self.db.consulta(
            "SELECT * FROM proyecto ORDER BY activo DESC, actualizado_en DESC")]

    def obtener(self, proyecto_id) -> Proyecto | None:
        fila = self.db.uno("SELECT * FROM proyecto WHERE id = ?", (proyecto_id,))
        if not fila:
            return None
        p = Proyecto.desde_fila(fila)
        for r in self.db.consulta(
                "SELECT * FROM proyecto_responsable WHERE proyecto_id = ?", (proyecto_id,)):
            p.responsables[r["rol"]] = Responsable(
                rol=r["rol"], **{k: (r[k] or "") for k in
                                 ("nombre", "profesion", "colegiatura", "dni", "telefono", "correo")})
        return p

    def obtener_activo(self) -> Proyecto | None:
        fila = self.db.uno("SELECT id FROM proyecto WHERE activo = 1")
        return self.obtener(fila["id"]) if fila else None

    # ---------- Validación ----------
    def validar(self, p: Proyecto) -> dict:
        e = {}
        if not p.razon_social.strip():
            e["razon_social"] = "La razón social / entidad es obligatoria."
        if not v.validar_ruc(p.ruc):
            e["ruc"] = "RUC inválido (11 dígitos, prefijo 10/15/16/17/20 y dígito verificador)."
        if p.correo and not v.validar_correo(p.correo):
            e["correo"] = "Correo de la entidad con formato inválido."
        if not p.nombre_obra.strip():
            e["nombre_obra"] = "El nombre de la obra es obligatorio."
        if p.cui and not v.validar_cui(p.cui):
            e["cui"] = "El CUI debe tener 6 o 7 dígitos numéricos."
        if p.modalidad not in MODALIDADES:
            e["modalidad"] = "Modalidad de ejecución no válida."
        if p.tipo_entidad not in TIPOS_ENTIDAD:
            e["tipo_entidad"] = "Tipo de entidad no válido."
        if p.estado not in ESTADOS:
            e["estado"] = "Estado de obra no válido."
        if p.modalidad == "CONTRATA":
            if not p.contratista.strip():
                e["contratista"] = "En obras por contrata indique el contratista."
            if p.contratista_ruc and not v.validar_ruc(p.contratista_ruc):
                e["contratista_ruc"] = "RUC del contratista inválido."
        if p.presupuesto is not None and p.presupuesto < 0:
            e["presupuesto"] = "El presupuesto no puede ser negativo."
        if not p.moneda_simbolo.strip():
            e["moneda_simbolo"] = "Indique el símbolo de moneda."

        try:
            fechas = {k: v.parse_fecha(getattr(p, k)) for k in
                      ("fecha_entrega_terreno", "fecha_inicio",
                       "fecha_termino_prog", "fecha_termino_real")}
        except ValueError:
            e["fecha_inicio"] = "Hay una fecha con formato inválido (use AAAA-MM-DD)."
            fechas = {}
        ini = fechas.get("fecha_inicio")
        if ini and fechas.get("fecha_termino_prog") and fechas["fecha_termino_prog"] < ini:
            e["fecha_termino_prog"] = "El término programado no puede ser anterior al inicio."
        if ini and fechas.get("fecha_termino_real") and fechas["fecha_termino_real"] < ini:
            e["fecha_termino_real"] = "El término real no puede ser anterior al inicio."
        if ini and fechas.get("fecha_entrega_terreno") and fechas["fecha_entrega_terreno"] > ini:
            e["fecha_entrega_terreno"] = "La entrega de terreno debe ser igual o anterior al inicio."
        if p.plazo_dias is not None and p.plazo_dias <= 0:
            e["plazo_dias"] = "El plazo debe ser mayor que cero."

        if not p.responsable("RESIDENTE").nombre.strip():
            e["resp_RESIDENTE_nombre"] = "Indique el nombre del residente de obra."
        for rol, r in p.responsables.items():
            if rol not in ROLES:
                e[f"resp_{rol}"] = f"Rol desconocido: {rol}"
                continue
            if r.vacio:
                continue
            nombre_rol = ROLES[rol]
            if not r.nombre.strip():
                e[f"resp_{rol}_nombre"] = f"{nombre_rol}: falta el nombre."
            if r.dni and not v.validar_dni(r.dni):
                e[f"resp_{rol}_dni"] = f"{nombre_rol}: el DNI debe tener 8 dígitos."
            if r.correo and not v.validar_correo(r.correo):
                e[f"resp_{rol}_correo"] = f"{nombre_rol}: correo inválido."
        return e

    # ---------- Escritura ----------
    def guardar(self, p: Proyecto) -> int:
        """Inserta o actualiza el proyecto y sus responsables en una sola transacción."""
        self._normalizar(p)
        errores = self.validar(p)
        if errores:
            raise ValidacionError(errores)

        campos = Proyecto.campos_editables()
        valores = [getattr(p, c) for c in campos]
        anterior = self.obtener(p.id) if p.id else None

        try:
            with self.db.transaccion() as c:
                if p.id is None:
                    hay_activo = c.execute("SELECT 1 FROM proyecto WHERE activo=1").fetchone()
                    cols = campos + ["activo"]
                    cur = c.execute(
                        f"INSERT INTO proyecto ({', '.join(cols)}) "
                        f"VALUES ({', '.join('?' * len(cols))})",
                        valores + [0 if hay_activo else 1])
                    p.id = cur.lastrowid
                    accion, detalle = "CREAR", {"nombre_obra": p.nombre_obra}
                else:
                    asignaciones = ", ".join(f"{c_} = ?" for c_ in campos)
                    c.execute(
                        f"UPDATE proyecto SET {asignaciones}, "
                        f"actualizado_en = datetime('now','localtime') WHERE id = ?",
                        valores + [p.id])
                    accion, detalle = "EDITAR", self._diferencias(anterior, p)

                c.execute("DELETE FROM proyecto_responsable WHERE proyecto_id = ?", (p.id,))
                for rol, r in p.responsables.items():
                    if r.vacio:
                        continue
                    c.execute(
                        "INSERT INTO proyecto_responsable "
                        "(proyecto_id, rol, nombre, profesion, colegiatura, dni, telefono, correo) "
                        "VALUES (?,?,?,?,?,?,?,?)",
                        (p.id, rol, r.nombre, r.profesion, r.colegiatura, r.dni, r.telefono, r.correo))

                self._auditar(c, accion, p.id, detalle)
        except sqlite3.IntegrityError as ex:
            if "ux_proyecto_cui" in str(ex) or "proyecto.cui" in str(ex):
                raise ValidacionError({"cui": "Ya existe otro proyecto con ese CUI."}) from ex
            raise
        return p.id

    def activar(self, proyecto_id: int):
        with self.db.transaccion() as c:
            c.execute("UPDATE proyecto SET activo = 0 WHERE activo = 1")
            c.execute("UPDATE proyecto SET activo = 1 WHERE id = ?", (proyecto_id,))
            self._auditar(c, "ACTIVAR", proyecto_id, None)

    def importar_logo(self, proyecto_id: int, origen: str) -> str:
        """Copia el logo a la carpeta de datos (el original puede moverse sin romper reportes)."""
        origen = Path(origen)
        if not origen.is_file():
            raise ValidacionError({"logo_path": "No se encontró el archivo de logo."})
        if origen.suffix.lower() not in (".png", ".jpg", ".jpeg", ".bmp"):
            raise ValidacionError({"logo_path": "El logo debe ser PNG, JPG o BMP."})
        if origen.stat().st_size > 5 * 1024 * 1024:
            raise ValidacionError({"logo_path": "El logo supera 5 MB."})
        destino = config.logos_dir() / f"proyecto_{proyecto_id}{origen.suffix.lower()}"
        for viejo in config.logos_dir().glob(f"proyecto_{proyecto_id}.*"):
            if viejo != destino:
                viejo.unlink(missing_ok=True)
        shutil.copyfile(origen, destino)
        return str(destino)

    def actualizar_logo(self, proyecto_id: int, origen: str | None) -> str:
        """Importa (o quita, si origen es None) el logo y lo registra en la BD."""
        destino = self.importar_logo(proyecto_id, origen) if origen else ""
        if not origen:
            for viejo in config.logos_dir().glob(f"proyecto_{proyecto_id}.*"):
                viejo.unlink(missing_ok=True)
        with self.db.transaccion() as c:
            c.execute("UPDATE proyecto SET logo_path = ?, actualizado_en = datetime('now','localtime') "
                      "WHERE id = ?", (destino, proyecto_id))
            self._auditar(c, "LOGO", proyecto_id, {"logo_path": destino or "(quitado)"})
        return destino

    # ---------- Utilidades ----------
    def completitud(self, p: Proyecto) -> tuple[int, list[str]]:
        """% de datos clave completos y lista de faltantes (para el indicador de la pantalla)."""
        clave = {
            "Razón social": p.razon_social, "RUC": p.ruc, "Dirección": p.direccion,
            "Nombre de obra": p.nombre_obra, "CUI": p.cui,
            "Distrito": p.distrito, "Provincia": p.provincia, "Departamento": p.departamento,
            "Fecha de inicio": p.fecha_inicio, "Término programado": p.fecha_termino_prog,
            "Residente": p.responsable("RESIDENTE").nombre,
            "Supervisor / Inspector": p.responsable("SUPERVISOR").nombre,
            "Almacenero": p.responsable("ALMACENERO").nombre,
            "Logo": p.logo_path,
        }
        faltan = [k for k, val in clave.items() if not val]
        return round(100 * (len(clave) - len(faltan)) / len(clave)), faltan

    @staticmethod
    def avance_temporal(p: Proyecto, hoy: date | None = None):
        """(días transcurridos, plazo, %). None si faltan fechas."""
        if not p.fecha_inicio or not p.plazo_dias:
            return None
        hoy = hoy or date.today()
        trans = (hoy - v.parse_fecha(p.fecha_inicio)).days + 1
        trans = max(0, min(trans, p.plazo_dias))
        return trans, p.plazo_dias, round(100 * trans / p.plazo_dias, 1)

    def _normalizar(self, p: Proyecto):
        for c in Proyecto.campos_editables():
            val = getattr(p, c)
            if isinstance(val, str):
                setattr(p, c, val.strip())
        p.ruc = p.ruc.replace(" ", "")
        p.cui = p.cui.replace(" ", "")
        for k in ("fecha_entrega_terreno", "fecha_inicio", "fecha_termino_prog", "fecha_termino_real"):
            if not getattr(p, k):
                setattr(p, k, None)
        if p.modalidad == "ADMINISTRACION_DIRECTA":
            p.contratista = p.contratista_ruc = p.numero_contrato = ""
        calculado = v.plazo_dias(p.fecha_inicio, p.fecha_termino_prog)
        if calculado:
            p.plazo_dias = calculado
        for r in p.responsables.values():
            for k in ("nombre", "profesion", "colegiatura", "dni", "telefono", "correo"):
                setattr(r, k, (getattr(r, k) or "").strip())

    @staticmethod
    def _diferencias(antes: Proyecto | None, despues: Proyecto) -> dict:
        if not antes:
            return {}
        cambios = {}
        for c in Proyecto.campos_editables():
            a, d = getattr(antes, c), getattr(despues, c)
            if (a or None) != (d or None):
                cambios[c] = {"antes": a, "despues": d}
        for rol in ROLES:
            a, d = antes.responsable(rol), despues.responsable(rol)
            if a != d:
                cambios[f"responsable_{rol}"] = {"antes": a.nombre, "despues": d.nombre}
        return cambios

    def _auditar(self, c, accion, entidad_id, detalle):
        c.execute(
            "INSERT INTO auditoria (usuario, modulo, accion, entidad, entidad_id, detalle) "
            "VALUES (?,?,?,?,?,?)",
            (self.usuario, self.MODULO, accion, "proyecto", entidad_id,
             json.dumps(detalle, ensure_ascii=False) if detalle else None))
