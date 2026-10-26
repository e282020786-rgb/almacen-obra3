"""Hoja de estilos (QSS) de la aplicación."""

AZUL_OSCURO = "#0f2a44"
AZUL = "#2563eb"
VERDE = "#059669"
ROJO = "#dc2626"

QSS = f"""
* {{ font-family: "Segoe UI", "Inter", Arial; font-size: 10pt; color: #1f2937; }}
QMainWindow, #contenido {{ background: #eef1f5; }}

/* ---------- Menú lateral ---------- */
#sidebar {{ background: {AZUL_OSCURO}; }}
#sidebar QLabel {{ color: #e5ecf4; }}
#sidebarEntidad {{ font-weight: 700; font-size: 10.5pt; color: white; }}
#sidebarObra {{ font-size: 8.5pt; color: #b9c7d8; }}
#sidebarSeccion {{ font-size: 8pt; font-weight: 700; color: #8fa3bb; letter-spacing: 1px; }}
#logoBox {{ background: white; border-radius: 12px; }}
QPushButton[nav="true"] {{
    background: transparent; color: #e5ecf4; text-align: left; padding: 9px 14px;
    border: 1px solid #23415f; border-radius: 6px; font-weight: 600;
}}
QPushButton[nav="true"]:hover {{ background: #1b3a5a; }}
QPushButton[nav="true"]:checked {{ background: white; color: {AZUL_OSCURO}; }}
QPushButton[nav="true"]:disabled {{ color: #5f7690; border-color: #1b3550; }}

/* ---------- Tarjetas ---------- */
#tarjeta {{ background: white; border: 1px solid #dde3ea; border-radius: 10px; }}
#tarjetaTitulo {{ font-size: 11pt; font-weight: 700; color: {AZUL_OSCURO}; }}
#tarjetaSub {{ font-size: 8.5pt; color: #6b7280; }}
#tituloPagina {{ font-size: 14pt; font-weight: 700; color: {AZUL_OSCURO}; }}
#badge {{ background: #d1fae5; color: #047857; border-radius: 10px; padding: 3px 12px;
          font-size: 8.5pt; font-weight: 700; }}
#badgeAviso {{ background: #fef3c7; color: #92400e; border-radius: 10px; padding: 3px 12px;
               font-size: 8.5pt; font-weight: 700; }}
#aviso {{ background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 8px 12px;
          color: #1e3a8a; }}
#etiquetaCampo {{ font-size: 8.5pt; color: #4b5563; font-weight: 600; }}
#ayuda {{ font-size: 8pt; color: #6b7280; }}

/* ---------- Campos ---------- */
QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox, QPlainTextEdit {{
    background: #f9fafb; border: 1px solid #d1d5db; border-radius: 6px; padding: 6px 8px;
    min-height: 18px;
}}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QDoubleSpinBox:focus,
QSpinBox:focus, QPlainTextEdit:focus {{ border: 1.5px solid {AZUL}; background: white; }}
*[error="true"] {{ border: 1.5px solid {ROJO}; background: #fef2f2; }}
QLineEdit:disabled, QComboBox:disabled {{ color: #9ca3af; background: #f3f4f6; }}

/* ---------- Botones ---------- */
QPushButton {{ border-radius: 6px; padding: 8px 16px; font-weight: 600;
               background: white; border: 1px solid #d1d5db; }}
QPushButton:hover {{ background: #f3f4f6; }}
QPushButton[tipo="primario"] {{ background: {AZUL}; color: white; border: none; }}
QPushButton[tipo="primario"]:hover {{ background: #1d4ed8; }}
QPushButton[tipo="exito"] {{ background: {VERDE}; color: white; border: none; }}
QPushButton[tipo="exito"]:hover {{ background: #047857; }}
QPushButton[tipo="peligro"] {{ background: {ROJO}; color: white; border: none; }}
QPushButton:disabled {{ background: #e5e7eb; color: #9ca3af; }}

QProgressBar {{ border: none; background: #e5e7eb; border-radius: 5px; height: 10px;
                text-align: center; font-size: 7pt; }}
QProgressBar::chunk {{ background: {VERDE}; border-radius: 5px; }}
QScrollArea {{ border: none; background: transparent; }}
QCheckBox {{ spacing: 6px; }}
"""
