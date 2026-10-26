"""Conexión SQLite con transacciones y migraciones por versión (PRAGMA user_version)."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

_DIR = Path(__file__).parent

# Cada entrada: (versión, archivo .sql). Agregar nuevas migraciones al final.
MIGRACIONES = [
    (1, "schema_v1.sql"),
]


class Database:
    def __init__(self, ruta):
        self.ruta = str(ruta)
        self.conn = sqlite3.connect(self.ruta, detect_types=0, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.migrar()

    def migrar(self):
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        for numero, archivo in MIGRACIONES:
            if numero > version:
                sql = (_DIR / archivo).read_text(encoding="utf-8")
                with self.transaccion() as c:
                    for sentencia in _dividir_sql(sql):
                        c.execute(sentencia)
                    c.execute(f"PRAGMA user_version = {numero}")

    @contextmanager
    def transaccion(self):
        """BEGIN IMMEDIATE ... COMMIT; ROLLBACK ante cualquier error."""
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            yield self.conn
        except Exception:
            self.conn.execute("ROLLBACK")
            raise
        else:
            self.conn.execute("COMMIT")

    def consulta(self, sql, params=()):
        return self.conn.execute(sql, params).fetchall()

    def uno(self, sql, params=()):
        return self.conn.execute(sql, params).fetchone()

    def cerrar(self):
        self.conn.close()


def _dividir_sql(sql: str):
    """Divide un script en sentencias (sin triggers con ';' internos en v1)."""
    lineas = [l for l in sql.splitlines() if not l.strip().startswith("--")]
    for s in "\n".join(lineas).split(";"):
        if s.strip():
            yield s
