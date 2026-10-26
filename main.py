"""Punto de entrada.  Ejecutar:  python main.py"""
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from app import config
from app.database.connection import Database
from app.services.proyecto_service import ProyectoService
from app.ui.main_window import MainWindow
from app.ui.theme import QSS


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setStyleSheet(QSS)
    try:
        db = Database(config.db_path())
    except Exception as ex:
        QMessageBox.critical(None, "Base de datos", f"No se pudo abrir la base de datos:\n{ex}")
        return 1
    ventana = MainWindow(ProyectoService(db, usuario="administrador"))
    ventana.show()
    codigo = app.exec()
    db.cerrar()
    return codigo


if __name__ == "__main__":
    sys.exit(main())
