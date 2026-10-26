"""Módulo: Datos Generales del Proyecto.

Registra la empresa/entidad, la obra, ubicación, responsables, fechas y la
configuración que identificará todos los reportes del almacén.
"""
from pathlib import Path

from PySide6.QtCore import Qt, QDate, QMarginsF, QRegularExpression, QTimer, QUrl, Signal
from PySide6.QtGui import (QDesktopServices, QImage, QKeySequence, QPageLayout, QPageSize,
                           QPixmap, QRegularExpressionValidator, QShortcut, QTextDocument)
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFrame,
                               QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QPlainTextEdit, QProgressBar, QPushButton, QScrollArea,
                               QSpinBox, QVBoxLayout, QWidget)

from app.core.models import (ESTADOS, MODALIDADES, MONEDAS, ROLES, TIPOS_ENTIDAD, Proyecto,
                             Responsable)
from app.services import encabezado_reporte as enc
from app.services.proyecto_service import ProyectoService, ValidacionError
from app.ui.widgets.comunes import FechaOpcional, Tarjeta, marcar_error

DEPARTAMENTOS = ["Amazonas", "Áncash", "Apurímac", "Arequipa", "Ayacucho", "Cajamarca", "Callao",
                 "Cusco", "Huancavelica", "Huánuco", "Ica", "Junín", "La Libertad", "Lambayeque",
                 "Lima", "Loreto", "Madre de Dios", "Moquegua", "Pasco", "Piura", "Puno",
                 "San Martín", "Tacna", "Tumbes", "Ucayali"]

FUENTES = ["Recursos Ordinarios", "Recursos Directamente Recaudados",
           "Recursos por Operaciones Oficiales de Crédito", "Donaciones y Transferencias",
           "Recursos Determinados", "Recursos propios (privado)"]

CAMPOS_RESP = [("nombre", "Nombres y apellidos"), ("profesion", "Profesión"),
               ("colegiatura", "N° de colegiatura (CIP/CAP)"), ("dni", "DNI"),
               ("telefono", "Teléfono"), ("correo", "Correo")]


def _validador(patron):
    return QRegularExpressionValidator(QRegularExpression(patron))


def _boton(texto, tipo=None, tooltip=""):
    b = QPushButton(texto)
    if tipo:
        b.setProperty("tipo", tipo)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if tooltip:
        b.setToolTip(tooltip)
    return b


class DatosGeneralesView(QWidget):
    proyecto_guardado = Signal()   # la ventana principal refresca la cabecera lateral

    def __init__(self, servicio: ProyectoService, parent=None):
        super().__init__(parent)
        self.s = servicio
        self.proyecto = Proyecto()
        self._cargando = False
        self._sync_plazo = False
        self._sucio = False
        self._logo_pendiente = None      # ruta elegida antes de guardar un proyecto nuevo
        self.campos = {}                 # nombre_campo -> widget
        self.resp = {rol: {} for rol in ROLES}

        self._construir()
        self._atajos()
        self._timer_preview = QTimer(self, singleShot=True, interval=250)
        self._timer_preview.timeout.connect(self._actualizar_preview)
        self.recargar()

    # =========================================================== construcción UI
    def _construir(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(16, 16, 16, 8)
        raiz.setSpacing(10)

        # --- cabecera
        cab = QFrame(objectName="tarjeta")
        hc = QHBoxLayout(cab)
        hc.setContentsMargins(18, 12, 18, 12)
        tit = QVBoxLayout()
        t = QLabel("Datos Generales del Proyecto", objectName="tituloPagina")
        st = QLabel("Información base de la obra: identifica todos los documentos y reportes del almacén.",
                    objectName="tarjetaSub")
        tit.addWidget(t)
        tit.addWidget(st)
        hc.addLayout(tit, 1)
        hc.addWidget(QLabel("Proyecto:", objectName="etiquetaCampo"))
        self.cmb_proyecto = QComboBox()
        self.cmb_proyecto.setMinimumWidth(320)
        self.cmb_proyecto.currentIndexChanged.connect(self._al_elegir_proyecto)
        hc.addWidget(self.cmb_proyecto)
        self.badge = QLabel("", objectName="badge")
        hc.addWidget(self.badge)
        raiz.addWidget(cab)

        # --- aviso de primer uso
        self.aviso = QLabel(
            "Registre los datos generales y guarde antes de iniciar el control del almacén. "
            "Los campos marcados con * son obligatorios.", objectName="aviso")
        self.aviso.setWordWrap(True)
        raiz.addWidget(self.aviso)

        # --- barra de acciones
        barra = QHBoxLayout()
        self.btn_nuevo = _boton("＋ Nuevo proyecto", tooltip="Ctrl+N")
        self.btn_guardar = _boton("💾 Guardar", "primario", "Ctrl+S")
        self.btn_deshacer = _boton("↺ Descartar cambios")
        self.btn_activar = _boton("✔ Usar como proyecto activo")
        self.btn_pdf = _boton("📄 Exportar ficha PDF", "exito")
        self.btn_imprimir = _boton("🖨 Imprimir", tooltip="Ctrl+P")
        for b in (self.btn_nuevo, self.btn_guardar, self.btn_deshacer, self.btn_activar):
            barra.addWidget(b)
        barra.addStretch(1)
        barra.addWidget(self.btn_pdf)
        barra.addWidget(self.btn_imprimir)
        raiz.addLayout(barra)
        self.btn_nuevo.clicked.connect(self.nuevo)
        self.btn_guardar.clicked.connect(self.guardar)
        self.btn_deshacer.clicked.connect(self._descartar)
        self.btn_activar.clicked.connect(self._activar)
        self.btn_pdf.clicked.connect(self.exportar_pdf)
        self.btn_imprimir.clicked.connect(self.imprimir)

        # --- área desplazable: formularios (izq.) + vista previa (der.)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        cont = QWidget(objectName="contenido")
        self.grid_main = QGridLayout(cont)
        self.grid_main.setContentsMargins(0, 0, 6, 0)
        self.grid_main.setSpacing(12)
        scroll.setWidget(cont)
        raiz.addWidget(scroll, 1)

        self.col_form = QVBoxLayout()
        self.col_form.setSpacing(12)
        self.col_prev = QVBoxLayout()
        self.col_prev.setSpacing(12)
        self.w_form = QWidget()
        self.w_form.setLayout(self.col_form)
        self.w_prev = QWidget()
        self.w_prev.setLayout(self.col_prev)
        self._layout_ancho = None

        self.col_form.addWidget(self._tarjeta_entidad())
        self.col_form.addWidget(self._tarjeta_obra())
        self.col_form.addWidget(self._tarjeta_ubicacion())
        self.col_form.addWidget(self._tarjeta_responsables())
        self.col_form.addWidget(self._tarjeta_fechas())
        self.col_form.addWidget(self._tarjeta_reportes())
        self.col_form.addStretch(1)

        self.col_prev.addWidget(self._tarjeta_preview())
        self.col_prev.addWidget(self._tarjeta_completitud())
        self.col_prev.addStretch(1)
        self._reubicar(ancho=True)

        self._conectar_cambios()

    def _reubicar(self, ancho: bool):
        """Diseño adaptable: 2 columnas en pantallas anchas, 1 columna en angostas."""
        if self._layout_ancho == ancho:
            return
        self._layout_ancho = ancho
        self.grid_main.removeWidget(self.w_form)
        self.grid_main.removeWidget(self.w_prev)
        if ancho:
            self.grid_main.addWidget(self.w_form, 0, 0)
            self.grid_main.addWidget(self.w_prev, 0, 1)
            self.grid_main.setColumnStretch(0, 3)
            self.grid_main.setColumnStretch(1, 2)
        else:
            self.grid_main.addWidget(self.w_prev, 0, 0)
            self.grid_main.addWidget(self.w_form, 1, 0)
            self.grid_main.setColumnStretch(0, 1)
            self.grid_main.setColumnStretch(1, 0)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._reubicar(self.width() >= 1100)

    # ---------------------------------------------------------------- tarjetas
    def _reg(self, nombre, widget):
        self.campos[nombre] = widget
        return widget

    def _tarjeta_entidad(self):
        t = Tarjeta("1. Empresa / Entidad",
                    "Quién ejecuta la obra. Aparece en la cabecera de todos los reportes.")
        cmb = self._reg("tipo_entidad", QComboBox())
        for k, v in TIPOS_ENTIDAD.items():
            cmb.addItem(v, k)
        t.campo(0, 0, "Tipo", cmb)
        ruc = self._reg("ruc", QLineEdit(placeholderText="11 dígitos"))
        ruc.setValidator(_validador(r"\d{0,11}"))
        t.campo(0, 1, "RUC *", ruc)
        self.lbl_ruc = QLabel("", objectName="ayuda")
        t.grid.addWidget(self.lbl_ruc, 2, 1)
        t.campo(1, 0, "Razón social / Entidad *",
                self._reg("razon_social", QLineEdit(placeholderText="Ej.: Municipalidad Distrital de …")), 2)
        t.campo(2, 0, "Dirección", self._reg("direccion", QLineEdit()), 2)
        t.campo(3, 0, "Teléfono", self._reg("telefono", QLineEdit()))
        t.campo(3, 1, "Correo", self._reg("correo", QLineEdit(placeholderText="correo@entidad.gob.pe")))

        fila_logo = QHBoxLayout()
        self.lbl_logo_min = QLabel()
        self.lbl_logo_min.setFixedSize(56, 56)
        self.lbl_logo_min.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_logo_min.setStyleSheet("border:1px dashed #cbd5e1;border-radius:6px;")
        self.lbl_logo_txt = QLabel("Sin logo", objectName="ayuda")
        self.lbl_logo_txt.setWordWrap(True)
        b_sel = _boton("🖼 Seleccionar logo")
        b_quitar = _boton("Quitar")
        b_sel.clicked.connect(self._elegir_logo)
        b_quitar.clicked.connect(self._quitar_logo)
        fila_logo.addWidget(self.lbl_logo_min)
        fila_logo.addWidget(self.lbl_logo_txt, 1)
        fila_logo.addWidget(b_sel)
        fila_logo.addWidget(b_quitar)
        lbl = QLabel("Logo (PNG/JPG, se copia a la carpeta de datos)", objectName="etiquetaCampo")
        t.grid.addWidget(lbl, 12, 0, 1, 2)
        t.grid.addLayout(fila_logo, 13, 0, 1, 2)
        return t

    def _tarjeta_obra(self):
        t = Tarjeta("2. Obra", "Datos del proyecto de inversión y de su ejecución.")
        nom = self._reg("nombre_obra", QPlainTextEdit())
        nom.setPlaceholderText("Nombre completo según expediente técnico / Invierte.pe")
        nom.setFixedHeight(64)
        nom.setTabChangesFocus(True)
        t.campo(0, 0, "Nombre de la obra *", nom, 2)
        t.campo(1, 0, "Nombre corto (para encabezados reducidos)",
                self._reg("nombre_corto", QLineEdit(placeholderText="Ej.: I.E. N° 2934 - Trujillo")))
        cui = self._reg("cui", QLineEdit(placeholderText="Código Único de Inversiones"))
        cui.setValidator(_validador(r"\d{0,7}"))
        t.campo(1, 1, "CUI", cui)
        mod = self._reg("modalidad", QComboBox())
        for k, v in MODALIDADES.items():
            mod.addItem(v, k)
        mod.currentIndexChanged.connect(self._al_cambiar_modalidad)
        t.campo(2, 0, "Modalidad de ejecución", mod)
        est = self._reg("estado", QComboBox())
        for k, v in ESTADOS.items():
            est.addItem(v, k)
        t.campo(2, 1, "Estado de la obra", est)
        t.campo(3, 0, "Contratista *", self._reg("contratista", QLineEdit()))
        rc = self._reg("contratista_ruc", QLineEdit())
        rc.setValidator(_validador(r"\d{0,11}"))
        t.campo(3, 1, "RUC del contratista", rc)
        t.campo(4, 0, "N° de contrato", self._reg("numero_contrato", QLineEdit()))
        ff = self._reg("fuente_financiamiento", QComboBox())
        ff.setEditable(True)
        ff.addItems([""] + FUENTES)
        t.campo(4, 1, "Fuente de financiamiento", ff)
        pres = self._reg("presupuesto", QDoubleSpinBox())
        pres.setRange(0, 9_999_999_999.99)
        pres.setDecimals(2)
        pres.setGroupSeparatorShown(True)
        pres.setSpecialValueText("—")
        pres.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        t.campo(5, 0, "Presupuesto / monto de obra", pres)
        return t

    def _tarjeta_ubicacion(self):
        t = Tarjeta("3. Ubicación", "Ubicación geográfica del proyecto.")
        dep = self._reg("departamento", QComboBox())
        dep.setEditable(True)
        dep.addItems([""] + DEPARTAMENTOS)
        t.campo(0, 0, "Departamento", dep)
        t.campo(0, 1, "Provincia", self._reg("provincia", QLineEdit()))
        t.campo(1, 0, "Distrito", self._reg("distrito", QLineEdit()))
        t.campo(1, 1, "Localidad / centro poblado / dirección de obra",
                self._reg("localidad", QLineEdit()))
        return t

    def _tarjeta_responsables(self):
        t = Tarjeta("4. Responsables",
                    "Personal que firma vales, guías y reportes. Deje en blanco el rol que no aplique.")
        fila = 0
        for rol, nombre_rol in ROLES.items():
            lbl = QLabel(nombre_rol + (" *" if rol == "RESIDENTE" else ""), objectName="tarjetaTitulo")
            lbl.setStyleSheet("font-size:10pt;margin-top:6px;")
            t.grid.addWidget(lbl, fila, 0, 1, 3)
            fila += 1
            for i, (campo, etiqueta) in enumerate(CAMPOS_RESP):
                w = QLineEdit()
                if campo == "dni":
                    w.setValidator(_validador(r"\d{0,8}"))
                self.resp[rol][campo] = w
                col = i % 3
                f = fila + (i // 3) * 2
                e = QLabel(etiqueta, objectName="etiquetaCampo")
                e.setBuddy(w)
                t.grid.addWidget(e, f, col)
                t.grid.addWidget(w, f + 1, col)
            fila += 4
        for c in range(3):
            t.grid.setColumnStretch(c, 2 if c == 0 else 1)
        return t

    def _tarjeta_fechas(self):
        t = Tarjeta("5. Fechas y plazo",
                    "El plazo se cuenta en días calendario incluyendo el día de inicio. "
                    "Al ingresar el plazo se calcula el término programado y viceversa.")
        t.campo(0, 0, "Entrega de terreno", self._reg("fecha_entrega_terreno", FechaOpcional()))
        t.campo(0, 1, "Inicio de obra", self._reg("fecha_inicio", FechaOpcional()))
        plazo = self._reg("plazo_dias", QSpinBox())
        plazo.setRange(0, 3650)
        plazo.setSpecialValueText("—")
        plazo.setSuffix(" días")
        t.campo(1, 0, "Plazo de ejecución", plazo)
        t.campo(1, 1, "Término programado", self._reg("fecha_termino_prog", FechaOpcional()))
        t.campo(2, 0, "Término real", self._reg("fecha_termino_real", FechaOpcional()))
        self.lbl_avance = QLabel("", objectName="ayuda")
        t.grid.addWidget(self.lbl_avance, 7, 1)
        plazo.valueChanged.connect(self._plazo_a_termino)
        self.campos["fecha_inicio"].cambiado.connect(self._plazo_a_termino)
        self.campos["fecha_termino_prog"].cambiado.connect(self._termino_a_plazo)
        return t

    def _tarjeta_reportes(self):
        t = Tarjeta("6. Personalización de reportes",
                    "Cómo se mostrará la información en Excel, PDF e impresiones.")
        mon = self._reg("moneda_codigo", QComboBox())
        for k, (sim, nom) in MONEDAS.items():
            mon.addItem(f"{k} – {nom}", k)
        mon.currentIndexChanged.connect(self._al_cambiar_moneda)
        t.campo(0, 0, "Moneda", mon)
        t.campo(0, 1, "Símbolo", self._reg("moneda_simbolo", QLineEdit()))
        t.campo(1, 0, "Denominación del año", self._reg(
            "denominacion_anio", QLineEdit(placeholderText="Texto oficial del año (se imprime arriba)")), 2)
        t.campo(2, 0, "Línea adicional del encabezado", self._reg(
            "encabezado_extra", QLineEdit(placeholderText="Ej.: Gerencia de Infraestructura – Sub Gerencia de Obras")), 2)
        t.campo(3, 0, "Pie de página", self._reg(
            "pie_reporte", QLineEdit(placeholderText="Ej.: Documento de control interno de almacén")), 2)
        checks = QHBoxLayout()
        for nombre, texto in (("mostrar_logo", "Mostrar logo"), ("firma_almacenero", "Firma almacenero"),
                              ("firma_residente", "Firma residente"), ("firma_supervisor", "Firma supervisor")):
            cb = self._reg(nombre, QCheckBox(texto))
            checks.addWidget(cb)
        checks.addStretch(1)
        t.grid.addLayout(checks, 12, 0, 1, 2)
        return t

    def _tarjeta_preview(self):
        t = Tarjeta("Vista previa del encabezado", "Así se verá en los reportes.")
        self.prev_logo = QLabel()
        self.prev_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.prev_html = QLabel()
        self.prev_html.setWordWrap(True)
        self.prev_html.setTextFormat(Qt.TextFormat.RichText)
        self.prev_html.setStyleSheet("background:white;border:1px solid #e5e7eb;padding:10px;")
        self.prev_html.setMinimumWidth(300)
        t.cuerpo.addWidget(self.prev_logo)
        t.cuerpo.addWidget(self.prev_html)
        return t

    def _tarjeta_completitud(self):
        t = Tarjeta("Estado de la información", "Datos clave para reportes correctamente identificados.")
        self.barra = QProgressBar()
        self.barra.setRange(0, 100)
        self.lbl_faltan = QLabel("", objectName="ayuda")
        self.lbl_faltan.setWordWrap(True)
        self.lbl_meta = QLabel("", objectName="ayuda")
        self.lbl_meta.setWordWrap(True)
        t.cuerpo.addWidget(self.barra)
        t.cuerpo.addWidget(self.lbl_faltan)
        t.cuerpo.addWidget(self.lbl_meta)
        return t

    def _atajos(self):
        QShortcut(QKeySequence(QKeySequence.StandardKey.Save), self).activated.connect(self.guardar)
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self.nuevo)
        QShortcut(QKeySequence(QKeySequence.StandardKey.Print), self).activated.connect(self.imprimir)

    # ===================================================== lectura / escritura del formulario
    @staticmethod
    def _leer(w):
        if isinstance(w, FechaOpcional):
            return w.valor()
        if isinstance(w, QPlainTextEdit):
            return " ".join(w.toPlainText().split())
        if isinstance(w, QComboBox):
            return w.currentText() if w.isEditable() else w.currentData()
        if isinstance(w, QDoubleSpinBox):
            return w.value() or None
        if isinstance(w, QSpinBox):
            return w.value() or None
        if isinstance(w, QCheckBox):
            return int(w.isChecked())
        return w.text()

    @staticmethod
    def _escribir(w, valor):
        if isinstance(w, FechaOpcional):
            w.set_valor(valor)
        elif isinstance(w, QPlainTextEdit):
            w.setPlainText(valor or "")
        elif isinstance(w, QComboBox):
            if w.isEditable():
                w.setCurrentText(valor or "")
            else:
                i = w.findData(valor)
                w.setCurrentIndex(max(i, 0))
        elif isinstance(w, (QDoubleSpinBox, QSpinBox)):
            w.setValue(valor or 0)
        elif isinstance(w, QCheckBox):
            w.setChecked(bool(valor))
        else:
            w.setText(valor or "")

    def _formulario_a_proyecto(self) -> Proyecto:
        p = Proyecto(id=self.proyecto.id, activo=self.proyecto.activo,
                     logo_path=self.proyecto.logo_path)
        for nombre, w in self.campos.items():
            setattr(p, nombre, self._leer(w))
        for rol, ws in self.resp.items():
            p.responsables[rol] = Responsable(rol, **{c: ws[c].text() for c, _ in CAMPOS_RESP})
        return p

    def _proyecto_a_formulario(self, p: Proyecto):
        self._cargando = True
        try:
            for nombre, w in self.campos.items():
                self._escribir(w, getattr(p, nombre))
            for rol, ws in self.resp.items():
                r = p.responsable(rol)
                for c, _ in CAMPOS_RESP:
                    ws[c].setText(getattr(r, c))
            self._al_cambiar_modalidad()
            self._limpiar_errores()
            self._mostrar_logo(self._logo_pendiente or p.logo_path)
        finally:
            self._cargando = False
        self._set_sucio(False)
        self._actualizar_preview()

    def _conectar_cambios(self):
        for w in list(self.campos.values()) + [w for d in self.resp.values() for w in d.values()]:
            if isinstance(w, FechaOpcional):
                w.cambiado.connect(self._al_editar)
            elif isinstance(w, QPlainTextEdit):
                w.textChanged.connect(self._al_editar)
            elif isinstance(w, QComboBox):
                w.currentIndexChanged.connect(self._al_editar)
                if w.isEditable():
                    w.editTextChanged.connect(self._al_editar)
            elif isinstance(w, (QDoubleSpinBox, QSpinBox)):
                w.valueChanged.connect(self._al_editar)
            elif isinstance(w, QCheckBox):
                w.toggled.connect(self._al_editar)
            else:
                w.textChanged.connect(self._al_editar)
        self.campos["ruc"].textChanged.connect(self._validar_ruc_vivo)

    def _al_editar(self, *_):
        if self._cargando:
            return
        self._set_sucio(True)
        self._timer_preview.start()

    def _set_sucio(self, sucio: bool):
        self._sucio = sucio
        self.btn_deshacer.setEnabled(sucio)
        self.btn_guardar.setText("💾 Guardar *" if sucio else "💾 Guardar")

    @property
    def tiene_cambios(self) -> bool:
        return self._sucio

    # =========================================================== reglas de pantalla
    def _al_cambiar_modalidad(self, *_):
        contrata = self.campos["modalidad"].currentData() == "CONTRATA"
        for n in ("contratista", "contratista_ruc", "numero_contrato"):
            self.campos[n].setEnabled(contrata)

    def _al_cambiar_moneda(self, *_):
        if self._cargando:
            return
        cod = self.campos["moneda_codigo"].currentData()
        self.campos["moneda_simbolo"].setText(MONEDAS[cod][0])

    def _validar_ruc_vivo(self, texto):
        from app.core.validators import validar_ruc
        if not texto:
            self.lbl_ruc.setText("")
        elif len(texto) < 11:
            self.lbl_ruc.setText(f"{len(texto)}/11 dígitos")
        elif validar_ruc(texto):
            self.lbl_ruc.setText("✔ RUC válido")
        else:
            self.lbl_ruc.setText("✖ Dígito verificador o prefijo incorrecto")

    def _plazo_a_termino(self, *_):
        if self._sync_plazo or self._cargando:
            return
        ini = self.campos["fecha_inicio"].valor()
        plazo = self.campos["plazo_dias"].value()
        if ini and plazo:
            self._sync_plazo = True
            fin = QDate.fromString(ini, "yyyy-MM-dd").addDays(plazo - 1)
            self.campos["fecha_termino_prog"].set_valor(fin.toString("yyyy-MM-dd"))
            self._sync_plazo = False

    def _termino_a_plazo(self, *_):
        if self._sync_plazo or self._cargando:
            return
        ini = self.campos["fecha_inicio"].valor()
        fin = self.campos["fecha_termino_prog"].valor()
        if ini and fin and fin >= ini:
            self._sync_plazo = True
            d = QDate.fromString(ini, "yyyy-MM-dd").daysTo(QDate.fromString(fin, "yyyy-MM-dd")) + 1
            self.campos["plazo_dias"].setValue(d)
            self._sync_plazo = False

    def _actualizar_preview(self):
        p = self._formulario_a_proyecto()
        if not p.razon_social and not p.nombre_obra:
            self.prev_html.setText("<i style='color:#9ca3af'>Complete la entidad y la obra para ver el encabezado.</i>")
        else:
            self.prev_html.setText(enc.encabezado_html(p, "VALE DE SALIDA N° 000001", usar_logo=False))
        logo = self._logo_pendiente or p.logo_path
        if p.mostrar_logo and logo and Path(logo).is_file():
            self.prev_logo.setPixmap(QPixmap(logo).scaled(
                90, 90, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.prev_logo.show()
        else:
            self.prev_logo.hide()

        pct, faltan = self.s.completitud(p)
        self.barra.setValue(pct)
        self.barra.setFormat(f"{pct} %")
        self.lbl_faltan.setText("Completo ✔" if not faltan else "Pendiente: " + ", ".join(faltan))
        av = self.s.avance_temporal(p)
        self.lbl_avance.setText(f"Avance temporal: {av[0]}/{av[1]} días ({av[2]} %)" if av else "")
        meta = []
        if self.proyecto.creado_en:
            meta.append(f"Creado: {self.proyecto.creado_en}")
        if self.proyecto.actualizado_en:
            meta.append(f"Última modificación: {self.proyecto.actualizado_en}")
        self.lbl_meta.setText(" · ".join(meta))

    # ================================================================== logo
    def _mostrar_logo(self, ruta):
        if ruta and Path(ruta).is_file():
            self.lbl_logo_min.setPixmap(QPixmap(ruta).scaled(
                52, 52, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.lbl_logo_txt.setText(Path(ruta).name + (" (se guardará con el proyecto)"
                                                          if ruta == self._logo_pendiente else ""))
        else:
            self.lbl_logo_min.clear()
            self.lbl_logo_txt.setText("Sin logo")

    def _elegir_logo(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Seleccionar logo", "",
                                              "Imágenes (*.png *.jpg *.jpeg *.bmp)")
        if not ruta:
            return
        if QPixmap(ruta).isNull():
            QMessageBox.warning(self, "Logo", "El archivo no es una imagen válida.")
            return
        if self.proyecto.id is None:
            self._logo_pendiente = ruta
            self._mostrar_logo(ruta)
            self._al_editar()
            return
        try:
            self.proyecto.logo_path = self.s.actualizar_logo(self.proyecto.id, ruta)
        except ValidacionError as e:
            QMessageBox.warning(self, "Logo", str(e))
            return
        self._mostrar_logo(self.proyecto.logo_path)
        self._actualizar_preview()
        self.proyecto_guardado.emit()

    def _quitar_logo(self):
        if self._logo_pendiente:
            self._logo_pendiente = None
        elif self.proyecto.id and self.proyecto.logo_path:
            if QMessageBox.question(self, "Quitar logo", "¿Quitar el logo de este proyecto?") \
                    != QMessageBox.StandardButton.Yes:
                return
            self.s.actualizar_logo(self.proyecto.id, None)
            self.proyecto.logo_path = ""
            self.proyecto_guardado.emit()
        self._mostrar_logo(None)
        self._actualizar_preview()

    # ============================================================ acciones
    def recargar(self, seleccionar_id=None):
        """Carga la lista de proyectos y muestra el indicado (o el activo)."""
        proyectos = self.s.listar()
        self.cmb_proyecto.blockSignals(True)
        self.cmb_proyecto.clear()
        for p in proyectos:
            marca = "● " if p.activo else "   "
            self.cmb_proyecto.addItem(f"{marca}{p.nombre_corto or p.nombre_obra[:60]}", p.id)
        self.cmb_proyecto.blockSignals(False)
        self.aviso.setVisible(not proyectos)
        if not proyectos:
            self._cargar(Proyecto())
            return
        objetivo = seleccionar_id or next((p.id for p in proyectos if p.activo), proyectos[0].id)
        self.cmb_proyecto.blockSignals(True)
        self.cmb_proyecto.setCurrentIndex(self.cmb_proyecto.findData(objetivo))
        self.cmb_proyecto.blockSignals(False)
        self._cargar(self.s.obtener(objetivo))

    def _cargar(self, p: Proyecto):
        self.proyecto = p
        self._logo_pendiente = None
        self._proyecto_a_formulario(p)
        self._actualizar_badge()

    def _actualizar_badge(self):
        if self.proyecto.id is None:
            self.badge.setText("NUEVO – SIN GUARDAR")
            self.badge.setObjectName("badgeAviso")
        elif self.proyecto.activo:
            self.badge.setText("● PROYECTO ACTIVO")
            self.badge.setObjectName("badge")
        else:
            self.badge.setText("INACTIVO")
            self.badge.setObjectName("badgeAviso")
        self.badge.style().unpolish(self.badge)
        self.badge.style().polish(self.badge)
        self.btn_activar.setEnabled(bool(self.proyecto.id) and not self.proyecto.activo)
        guardado = self.proyecto.id is not None
        self.btn_pdf.setEnabled(guardado)
        self.btn_imprimir.setEnabled(guardado)

    def confirmar_descartar(self) -> bool:
        """True si se puede abandonar el formulario (no hay cambios o el usuario acepta)."""
        if not self._sucio:
            return True
        r = QMessageBox.question(
            self, "Cambios sin guardar",
            "Hay cambios sin guardar en Datos Generales.\n¿Desea guardarlos?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Save)
        if r == QMessageBox.StandardButton.Save:
            return self.guardar()
        return r == QMessageBox.StandardButton.Discard

    def _al_elegir_proyecto(self, indice):
        pid = self.cmb_proyecto.itemData(indice)
        if pid is None or pid == self.proyecto.id:
            return
        if not self.confirmar_descartar():
            self.cmb_proyecto.blockSignals(True)
            self.cmb_proyecto.setCurrentIndex(self.cmb_proyecto.findData(self.proyecto.id))
            self.cmb_proyecto.blockSignals(False)
            return
        self._cargar(self.s.obtener(pid))

    def nuevo(self):
        if not self.confirmar_descartar():
            return
        base = Proyecto()
        # Reutiliza los datos de la entidad del proyecto actual (caso típico: misma municipalidad).
        if self.proyecto.id and QMessageBox.question(
                self, "Nuevo proyecto",
                "¿Copiar los datos de la empresa/entidad y la configuración de reportes "
                "del proyecto actual?") == QMessageBox.StandardButton.Yes:
            for c in ("tipo_entidad", "razon_social", "ruc", "direccion", "telefono", "correo",
                      "moneda_codigo", "moneda_simbolo", "denominacion_anio", "encabezado_extra",
                      "pie_reporte", "mostrar_logo", "firma_residente", "firma_supervisor",
                      "firma_almacenero"):
                setattr(base, c, getattr(self.proyecto, c))
            if self.proyecto.logo_path:
                self._logo_pendiente_copiar = self.proyecto.logo_path
        self.cmb_proyecto.blockSignals(True)
        self.cmb_proyecto.setCurrentIndex(-1)
        self.cmb_proyecto.blockSignals(False)
        self._cargar(base)
        if getattr(self, "_logo_pendiente_copiar", None):
            self._logo_pendiente = self._logo_pendiente_copiar
            self._logo_pendiente_copiar = None
            self._mostrar_logo(self._logo_pendiente)
            self._actualizar_preview()
        self.campos["razon_social"].setFocus()

    def _limpiar_errores(self):
        for w in list(self.campos.values()) + [w for d in self.resp.values() for w in d.values()]:
            marcar_error(w, False)

    def _widget_de_error(self, clave):
        if clave in self.campos:
            return self.campos[clave]
        if clave.startswith("resp_"):
            _, rol, *resto = clave.split("_", 2)
            if resto and resto[0] in self.resp.get(rol, {}):
                return self.resp[rol][resto[0]]
        return None

    def guardar(self) -> bool:
        self._limpiar_errores()
        p = self._formulario_a_proyecto()
        es_nuevo = p.id is None
        try:
            pid = self.s.guardar(p)
        except ValidacionError as e:
            primero = None
            for clave in e.errores:
                w = self._widget_de_error(clave)
                if w is not None:
                    marcar_error(w, True)
                    primero = primero or w
            QMessageBox.warning(self, "Revise los datos",
                                "No se guardó. Corrija lo siguiente:\n\n• " + "\n• ".join(e.errores.values()))
            if primero:
                primero.setFocus()
            return False
        except Exception as ex:  # error inesperado de BD: no se perdió nada (rollback)
            QMessageBox.critical(self, "Error al guardar", f"No se pudo guardar.\n\n{ex}")
            return False

        if self._logo_pendiente:
            try:
                self.s.actualizar_logo(pid, self._logo_pendiente)
            except ValidacionError as e:
                QMessageBox.warning(self, "Logo", f"Los datos se guardaron, pero el logo no: {e}")
            self._logo_pendiente = None

        self._set_sucio(False)
        self.recargar(seleccionar_id=pid)
        self.proyecto_guardado.emit()
        if es_nuevo and self.proyecto.activo:
            QMessageBox.information(self, "Proyecto creado",
                                    "Datos generales guardados. Este es ahora el proyecto activo "
                                    "con el que trabajará el almacén.")
        return True

    def _descartar(self):
        if self._sucio and QMessageBox.question(
                self, "Descartar cambios", "¿Descartar los cambios no guardados?") \
                == QMessageBox.StandardButton.Yes:
            if self.proyecto.id:
                self._cargar(self.s.obtener(self.proyecto.id))
            else:
                self._cargar(Proyecto())

    def _activar(self):
        if not self.proyecto.id or not self.confirmar_descartar():
            return
        if QMessageBox.question(
                self, "Proyecto activo",
                f"¿Trabajar el almacén con la obra:\n\n{self.proyecto.nombre_obra}?") \
                != QMessageBox.StandardButton.Yes:
            return
        self.s.activar(self.proyecto.id)
        self.recargar(seleccionar_id=self.proyecto.id)
        self.proyecto_guardado.emit()

    # ============================================================ PDF / impresión
    def _documento_ficha(self) -> QTextDocument | None:
        if self.proyecto.id is None:
            return None
        if self._sucio:
            if QMessageBox.question(self, "Guardar primero",
                                    "La ficha se genera con los datos guardados. ¿Guardar ahora?") \
                    != QMessageBox.StandardButton.Yes or not self.guardar():
                return None
        p = self.s.obtener(self.proyecto.id)
        doc = QTextDocument()
        if p.logo_path and Path(p.logo_path).is_file():
            doc.addResource(QTextDocument.ResourceType.ImageResource,
                            QUrl(enc.LOGO_RESOURCE), QImage(p.logo_path))
        doc.setHtml(enc.ficha_html(p, self.s.avance_temporal(p)))
        return doc

    @staticmethod
    def _impresora(salida_pdf=None) -> QPrinter:
        pr = QPrinter(QPrinter.PrinterMode.HighResolution)
        pr.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        pr.setPageMargins(QMarginsF(15, 12, 15, 12), QPageLayout.Unit.Millimeter)
        if salida_pdf:
            pr.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            pr.setOutputFileName(salida_pdf)
        return pr

    def exportar_pdf(self):
        doc = self._documento_ficha()
        if doc is None:
            return
        sugerido = f"Ficha_Datos_Generales_{self.proyecto.cui or self.proyecto.id}.pdf"
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar ficha PDF", sugerido, "PDF (*.pdf)")
        if not ruta:
            return
        if not ruta.lower().endswith(".pdf"):
            ruta += ".pdf"
        doc.print_(self._impresora(ruta))
        if QMessageBox.question(self, "PDF generado", f"Ficha guardada en:\n{ruta}\n\n¿Abrir el archivo?") \
                == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl.fromLocalFile(ruta))

    def imprimir(self):
        doc = self._documento_ficha()
        if doc is None:
            return
        dlg = QPrintPreviewDialog(self._impresora(), self)
        dlg.setWindowTitle("Vista previa – Ficha de datos generales")
        dlg.paintRequested.connect(doc.print_)
        dlg.resize(900, 1000)
        dlg.exec()
