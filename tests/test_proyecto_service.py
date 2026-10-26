"""Pruebas del módulo Datos Generales (sin interfaz).  Ejecutar:  python -m unittest -v"""
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

TMP = tempfile.mkdtemp()
os.environ["ALMACEN_DATA_DIR"] = TMP

from app.core import validators as v  # noqa: E402
from app.core.models import Proyecto, Responsable  # noqa: E402
from app.database.connection import Database  # noqa: E402
from app.services.proyecto_service import ProyectoService, ValidacionError  # noqa: E402

RUC_OK = "20131312955"


def proyecto_base(**kw):
    p = Proyecto(razon_social="Municipalidad Distrital de Prueba", ruc=RUC_OK,
                 nombre_obra="Mejoramiento de la I.E. N° 001", cui="2567753",
                 distrito="Distrito", provincia="Provincia", departamento="Departamento",
                 fecha_inicio="2026-01-05", fecha_termino_prog="2026-05-04")
    p.responsables["RESIDENTE"] = Responsable("RESIDENTE", nombre="Ing. Residente", colegiatura="CIP 1")
    p.responsables["ALMACENERO"] = Responsable("ALMACENERO", nombre="Almacenero", dni="12345678")
    for k, val in kw.items():
        setattr(p, k, val)
    return p


class TestValidadores(unittest.TestCase):
    def test_ruc(self):
        self.assertTrue(v.validar_ruc(RUC_OK))
        self.assertFalse(v.validar_ruc("20131312954"))   # verificador incorrecto
        self.assertFalse(v.validar_ruc("30131312955"))   # prefijo inválido
        self.assertFalse(v.validar_ruc("2013131295"))    # 10 dígitos

    def test_plazo(self):
        self.assertEqual(v.plazo_dias("2026-01-01", "2026-01-30"), 30)
        self.assertIsNone(v.plazo_dias("2026-01-01", None))


class TestServicio(unittest.TestCase):
    def setUp(self):
        self.ruta = Path(TMP) / f"t_{self._testMethodName}.db"
        self.db = Database(self.ruta)
        self.s = ProyectoService(self.db, usuario="test")

    def tearDown(self):
        self.db.cerrar()

    def test_crear_y_persistir(self):
        pid = self.s.guardar(proyecto_base())
        self.db.cerrar()
        self.db = Database(self.ruta)                    # reabrir: persistencia real
        self.s = ProyectoService(self.db)
        p = self.s.obtener_activo()
        self.assertEqual(p.id, pid)
        self.assertEqual(p.plazo_dias, 120)
        self.assertEqual(p.responsable("RESIDENTE").colegiatura, "CIP 1")
        self.assertEqual(p.activo, 1)

    def test_validaciones(self):
        with self.assertRaises(ValidacionError) as cm:
            self.s.guardar(proyecto_base(ruc="123", nombre_obra="",
                                         fecha_termino_prog="2025-12-01"))
        self.assertIn("ruc", cm.exception.errores)
        self.assertIn("nombre_obra", cm.exception.errores)
        self.assertIn("fecha_termino_prog", cm.exception.errores)
        self.assertEqual(self.db.uno("SELECT COUNT(*) n FROM proyecto")["n"], 0)

    def test_contrata_requiere_contratista(self):
        with self.assertRaises(ValidacionError) as cm:
            self.s.guardar(proyecto_base(modalidad="CONTRATA"))
        self.assertIn("contratista", cm.exception.errores)

    def test_cui_duplicado(self):
        self.s.guardar(proyecto_base())
        with self.assertRaises(ValidacionError) as cm:
            self.s.guardar(proyecto_base())
        self.assertIn("cui", cm.exception.errores)

    def test_editar_y_auditoria(self):
        pid = self.s.guardar(proyecto_base())
        p = self.s.obtener(pid)
        p.nombre_obra = "Obra renombrada"
        p.responsables["SUPERVISOR"] = Responsable("SUPERVISOR", nombre="Ing. Supervisor")
        self.s.guardar(p)
        p2 = self.s.obtener(pid)
        self.assertEqual(p2.nombre_obra, "Obra renombrada")
        self.assertEqual(p2.responsable("SUPERVISOR").nombre, "Ing. Supervisor")
        filas = self.db.consulta("SELECT accion, detalle FROM auditoria ORDER BY id")
        self.assertEqual([f["accion"] for f in filas], ["CREAR", "EDITAR"])
        self.assertIn("nombre_obra", filas[1]["detalle"])

    def test_un_solo_activo(self):
        a = self.s.guardar(proyecto_base())
        b = self.s.guardar(proyecto_base(cui="1234567"))
        self.assertEqual(self.s.obtener(b).activo, 0)
        self.s.activar(b)
        self.assertEqual(self.s.obtener_activo().id, b)
        self.assertEqual(self.s.obtener(a).activo, 0)

    def test_avance_temporal(self):
        p = self.s.obtener(self.s.guardar(proyecto_base()))
        trans, plazo, pct = self.s.avance_temporal(p, hoy=date(2026, 1, 14))
        self.assertEqual((trans, plazo), (10, 120))
        self.assertAlmostEqual(pct, 8.3)

    def test_logo(self):
        pid = self.s.guardar(proyecto_base())
        origen = Path(TMP) / "logo.png"
        origen.write_bytes(b"\x89PNG\r\n\x1a\n")
        destino = self.s.importar_logo(pid, str(origen))
        self.assertTrue(Path(destino).is_file())
        with self.assertRaises(ValidacionError):
            self.s.importar_logo(pid, str(Path(TMP) / "no_existe.png"))


class TestEncabezado(unittest.TestCase):
    def test_ficha_html(self):
        from app.services import encabezado_reporte as enc
        p = proyecto_base(denominacion_anio="Año de prueba", presupuesto=1564699.06, plazo_dias=120)
        html = enc.ficha_html(p, (10, 120, 8.3))
        self.assertIn("FICHA DE DATOS GENERALES", html)
        self.assertIn("S/ 1,564,699.06", html)
        self.assertIn("Ing. Residente", html)
        self.assertIn("05/01/2026", html)
        p.razon_social = "<script>"
        self.assertNotIn("<script>", enc.encabezado_html(p))


if __name__ == "__main__":
    unittest.main()
