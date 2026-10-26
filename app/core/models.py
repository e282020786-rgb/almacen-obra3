"""Modelos de datos del módulo Datos Generales."""
from dataclasses import dataclass, field, fields, asdict
from typing import Optional

ROLES = {
    "RESIDENTE": "Residente de obra",
    "SUPERVISOR": "Supervisor / Inspector",
    "ALMACENERO": "Almacenero",
    "ADMINISTRADOR": "Administrador de obra",
}

TIPOS_ENTIDAD = {
    "ENTIDAD_PUBLICA": "Entidad pública",
    "EMPRESA_PRIVADA": "Empresa privada",
    "CONSORCIO": "Consorcio",
}

MODALIDADES = {
    "ADMINISTRACION_DIRECTA": "Administración directa",
    "CONTRATA": "Contrata",
}

ESTADOS = {
    "EN_EJECUCION": "En ejecución",
    "PARALIZADA": "Paralizada",
    "CULMINADA": "Culminada",
    "LIQUIDADA": "Liquidada",
}

MONEDAS = {  # código: (símbolo, nombre)
    "PEN": ("S/", "Soles"),
    "USD": ("US$", "Dólares americanos"),
    "EUR": ("€", "Euros"),
}


@dataclass
class Responsable:
    rol: str
    nombre: str = ""
    profesion: str = ""
    colegiatura: str = ""
    dni: str = ""
    telefono: str = ""
    correo: str = ""

    @property
    def vacio(self) -> bool:
        return not any(v.strip() for k, v in asdict(self).items() if k != "rol")


@dataclass
class Proyecto:
    id: Optional[int] = None
    activo: int = 0
    estado: str = "EN_EJECUCION"
    tipo_entidad: str = "ENTIDAD_PUBLICA"
    razon_social: str = ""
    ruc: str = ""
    direccion: str = ""
    telefono: str = ""
    correo: str = ""
    logo_path: str = ""
    nombre_obra: str = ""
    nombre_corto: str = ""
    cui: str = ""
    modalidad: str = "ADMINISTRACION_DIRECTA"
    contratista: str = ""
    contratista_ruc: str = ""
    numero_contrato: str = ""
    fuente_financiamiento: str = ""
    presupuesto: Optional[float] = None
    departamento: str = ""
    provincia: str = ""
    distrito: str = ""
    localidad: str = ""
    fecha_entrega_terreno: Optional[str] = None
    fecha_inicio: Optional[str] = None
    plazo_dias: Optional[int] = None
    fecha_termino_prog: Optional[str] = None
    fecha_termino_real: Optional[str] = None
    moneda_codigo: str = "PEN"
    moneda_simbolo: str = "S/"
    denominacion_anio: str = ""
    encabezado_extra: str = ""
    pie_reporte: str = ""
    mostrar_logo: int = 1
    firma_residente: int = 1
    firma_supervisor: int = 1
    firma_almacenero: int = 1
    creado_en: Optional[str] = None
    actualizado_en: Optional[str] = None
    responsables: dict = field(default_factory=dict)  # rol -> Responsable

    # Campos que se guardan desde el formulario (excluye id/fechas de sistema/responsables).
    @classmethod
    def campos_editables(cls):
        excluir = {"id", "activo", "creado_en", "actualizado_en", "responsables"}
        return [f.name for f in fields(cls) if f.name not in excluir]

    @classmethod
    def desde_fila(cls, fila):
        datos = {k: fila[k] for k in fila.keys() if k in {f.name for f in fields(cls)}}
        for k, v in datos.items():
            if v is None and isinstance(getattr(cls, k, None), str):
                datos[k] = ""
        return cls(**datos)

    @property
    def ubicacion(self) -> str:
        partes = [self.localidad, self.distrito, self.provincia, self.departamento]
        return " - ".join(p for p in partes if p)

    def responsable(self, rol) -> Responsable:
        return self.responsables.get(rol) or Responsable(rol=rol)
