"""Validaciones de datos peruanos y generales."""
import re
from datetime import date

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


def validar_ruc(ruc: str) -> bool:
    """RUC SUNAT: 11 dígitos, prefijo válido y dígito verificador módulo 11."""
    if not ruc or not re.fullmatch(r"\d{11}", ruc):
        return False
    if ruc[:2] not in ("10", "15", "16", "17", "20"):
        return False
    pesos = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    resto = 11 - sum(int(d) * p for d, p in zip(ruc[:10], pesos)) % 11
    verificador = {10: 0, 11: 1}.get(resto, resto)
    return verificador == int(ruc[10])


def validar_correo(correo: str) -> bool:
    return bool(_EMAIL.match(correo or ""))


def validar_cui(cui: str) -> bool:
    """CUI de Invierte.pe: numérico de 6 a 7 dígitos."""
    return bool(re.fullmatch(r"\d{6,7}", cui or ""))


def validar_dni(dni: str) -> bool:
    return bool(re.fullmatch(r"\d{8}", dni or ""))


def parse_fecha(valor):
    if not valor:
        return None
    return date.fromisoformat(valor)


def plazo_dias(inicio: str, termino: str):
    """Plazo en días calendario contando el día de inicio (inicio=1, término=N)."""
    i, t = parse_fecha(inicio), parse_fecha(termino)
    if not i or not t:
        return None
    return (t - i).days + 1
