"""Rutas y parámetros globales de la aplicación."""
import os
import sys
from pathlib import Path

APP_NAME = "AlmacenObra"
APP_TITULO = "Almacén de Obra"
APP_VERSION = "0.1.0"
DB_FILENAME = "almacen.db"


def data_dir() -> Path:
    """Carpeta de datos persistentes.

    Prioridad: variable ALMACEN_DATA_DIR > %APPDATA%\\AlmacenObra (Windows)
    > ~/.almacenobra (otros sistemas).
    """
    base = os.environ.get("ALMACEN_DATA_DIR")
    if base:
        ruta = Path(base)
    elif sys.platform == "win32":
        ruta = Path(os.environ.get("APPDATA", str(Path.home()))) / APP_NAME
    else:
        ruta = Path.home() / f".{APP_NAME.lower()}"
    ruta.mkdir(parents=True, exist_ok=True)
    (ruta / "logos").mkdir(exist_ok=True)
    return ruta


def db_path() -> Path:
    return data_dir() / DB_FILENAME


def logos_dir() -> Path:
    return data_dir() / "logos"
