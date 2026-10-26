"""Ventana principal: menú lateral con identificación de la obra + área de módulos."""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow,
                               QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from app import config
from app.services.proyecto_service import ProyectoService
from app.ui.modules.datos_generales import DatosGeneralesView

# Módulos del sistema. Los que aún no están construidos se muestran deshabilitados
# (no se simulan pantallas vacías ni datos ficticios).
MODULOS = [
    ("datos", "🏗  Datos generales", True),
    ("dashboard", "📊  Dashboard", False),
    ("items", "📦  Ítems / Productos", False),
    ("almacenes", "🏬  Almacenes", False),
    ("movimientos", "🔄  Movimientos", False),
    ("kardex", "📒  Kardex / Stock", False),
    ("reportes", "🧾  Reportes", False),
    ("usuarios", "👥  Usuarios", False),
    ("config", "⚙  Configuración", False),
]


class MainWindow(QMainWindow):
    def __init__(self, servicio: ProyectoService):
        super().__init__()
        self.s = servicio
        self.setWindowTitle(f"{config.APP_TITULO} v{config.APP_VERSION}")
        self.resize(1360, 860)
        self.setMinimumSize(980, 640)

        central = QWidget()
        h = QHBoxLayout(central)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        h.addWidget(self._sidebar())

        der = QWidget(objectName="contenido")
        v = QVBoxLayout(der)
        v.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        v.addWidget(self.stack, 1)
        pie = QLabel(f"© 2026 {config.APP_TITULO} · Datos en: {config.data_dir()}", objectName="ayuda")
        pie.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pie.setContentsMargins(0, 2, 0, 6)
        v.addWidget(pie)
        h.addWidget(der, 1)
        self.setCentralWidget(central)

        self.vista_datos = DatosGeneralesView(self.s)
        self.vista_datos.proyecto_guardado.connect(self.refrescar_cabecera)
        self.stack.addWidget(self.vista_datos)
        self.botones["datos"].setChecked(True)
        self.refrescar_cabecera()

    def _sidebar(self):
        sb = QFrame(objectName="sidebar")
        sb.setFixedWidth(250)
        v = QVBoxLayout(sb)
        v.setContentsMargins(16, 18, 16, 14)
        v.setSpacing(6)

        self.logo = QLabel(objectName="logoBox")
        self.logo.setFixedSize(96, 96)
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fila = QHBoxLayout()
        fila.addStretch(1)
        fila.addWidget(self.logo)
        fila.addStretch(1)
        v.addLayout(fila)
        self.lbl_entidad = QLabel(objectName="sidebarEntidad")
        self.lbl_obra = QLabel(objectName="sidebarObra")
        for l in (self.lbl_entidad, self.lbl_obra):
            l.setWordWrap(True)
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v.addWidget(l)
        v.addSpacing(14)
        v.addWidget(QLabel("NAVEGACIÓN", objectName="sidebarSeccion"))

        self.botones = {}
        grupo = QButtonGroup(self)
        grupo.setExclusive(True)
        for clave, texto, listo in MODULOS:
            b = QPushButton(texto)
            b.setProperty("nav", True)
            b.setCheckable(True)
            b.setEnabled(listo)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            if not listo:
                b.setToolTip("Módulo de la siguiente etapa de desarrollo")
            grupo.addButton(b)
            self.botones[clave] = b
            v.addWidget(b)
        v.addStretch(1)
        salir = QPushButton("✕  Salir")
        salir.clicked.connect(self.close)
        v.addWidget(salir)
        return sb

    def refrescar_cabecera(self):
        p = self.s.obtener_activo()
        if not p:
            self.lbl_entidad.setText("Sin proyecto activo")
            self.lbl_obra.setText("Registre los datos generales")
            self.logo.setText("🏗")
            return
        self.lbl_entidad.setText(p.razon_social.upper())
        self.lbl_obra.setText(p.nombre_corto or p.nombre_obra)
        if p.logo_path and Path(p.logo_path).is_file():
            self.logo.setPixmap(QPixmap(p.logo_path).scaled(
                84, 84, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.logo.clear()
            self.logo.setText("🏗")

    def closeEvent(self, ev):
        if self.vista_datos.confirmar_descartar():
            ev.accept()
        else:
            ev.ignore()
