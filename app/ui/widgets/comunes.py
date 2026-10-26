"""Widgets reutilizables: tarjeta, campo de fecha opcional y helpers de formulario."""
from PySide6.QtCore import QDate, QTimer, Signal, Qt
from PySide6.QtWidgets import (QDateEdit, QFrame, QHBoxLayout, QLabel, QToolButton,
                               QVBoxLayout, QWidget, QGridLayout)

FECHA_NULA = QDate(1900, 1, 1)


class Tarjeta(QFrame):
    """Contenedor blanco con título, subtítulo y una grilla de campos."""

    def __init__(self, titulo, subtitulo="", parent=None):
        super().__init__(parent)
        self.setObjectName("tarjeta")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 16)
        lay.setSpacing(10)
        t = QLabel(titulo)
        t.setObjectName("tarjetaTitulo")
        lay.addWidget(t)
        if subtitulo:
            s = QLabel(subtitulo)
            s.setObjectName("tarjetaSub")
            s.setWordWrap(True)
            lay.addWidget(s)
        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(14)
        self.grid.setVerticalSpacing(4)
        lay.addLayout(self.grid)
        self.cuerpo = lay

    def campo(self, fila, col, etiqueta, widget, colspan=1, ayuda=""):
        """Coloca 'etiqueta' arriba y el widget debajo (dos filas de grilla por campo)."""
        lbl = QLabel(etiqueta)
        lbl.setObjectName("etiquetaCampo")
        lbl.setBuddy(widget)
        self.grid.addWidget(lbl, fila * 3, col, 1, colspan)
        self.grid.addWidget(widget, fila * 3 + 1, col, 1, colspan)
        if ayuda:
            a = QLabel(ayuda)
            a.setObjectName("ayuda")
            a.setWordWrap(True)
            self.grid.addWidget(a, fila * 3 + 2, col, 1, colspan)
        return widget


class _DateEdit(QDateEdit):
    """Si está en 'Sin fecha', el calendario se abre en el mes actual y no en 1900."""

    def mousePressEvent(self, ev):
        super().mousePressEvent(ev)
        if self.date() == FECHA_NULA:
            hoy = QDate.currentDate()
            QTimer.singleShot(0, lambda: self.calendarWidget().setCurrentPage(hoy.year(), hoy.month()))


class FechaOpcional(QWidget):
    """QDateEdit con calendario que admite 'sin fecha'.  valor() -> 'AAAA-MM-DD' | None."""

    cambiado = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self.edit = _DateEdit()
        self.edit.setCalendarPopup(True)
        self.edit.setDisplayFormat("dd/MM/yyyy")
        self.edit.setMinimumDate(FECHA_NULA)
        self.edit.setSpecialValueText("Sin fecha")
        self.edit.setDate(FECHA_NULA)
        self.edit.calendarWidget().setGridVisible(True)
        self.btn = QToolButton()
        self.btn.setText("✕")
        self.btn.setToolTip("Quitar fecha")
        self.btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn.clicked.connect(self.limpiar)
        lay.addWidget(self.edit, 1)
        lay.addWidget(self.btn)
        self.setFocusProxy(self.edit)
        self.edit.dateChanged.connect(lambda _d: self.cambiado.emit())

    def valor(self):
        d = self.edit.date()
        return None if d == FECHA_NULA else d.toString("yyyy-MM-dd")

    def set_valor(self, iso):
        d = QDate.fromString(iso, "yyyy-MM-dd") if iso else FECHA_NULA
        self.edit.setDate(d if d.isValid() else FECHA_NULA)

    def limpiar(self):
        self.edit.setDate(FECHA_NULA)

    def set_error(self, error: bool):
        self.edit.setProperty("error", error)
        self.edit.style().unpolish(self.edit)
        self.edit.style().polish(self.edit)


def marcar_error(widget, error: bool):
    if isinstance(widget, FechaOpcional):
        widget.set_error(error)
        return
    widget.setProperty("error", error)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
