"""Encabezado, firmas y ficha en HTML a partir de los Datos Generales.

Todos los reportes futuros (PDF/impresión) reutilizan estas funciones, así la
identificación de la obra sale igual en cada documento.
"""
from html import escape
from datetime import date

from app.core.models import Proyecto, ROLES, MODALIDADES, ESTADOS, TIPOS_ENTIDAD, MONEDAS

LOGO_RESOURCE = "logo_proyecto"   # nombre de recurso para QTextDocument.addResource


def _e(t):
    return escape(t or "")


def _fecha(iso):
    if not iso:
        return "—"
    d = date.fromisoformat(iso)
    return d.strftime("%d/%m/%Y")


def _monto(p: Proyecto):
    if p.presupuesto is None:
        return "—"
    return f"{p.moneda_simbolo} {p.presupuesto:,.2f}"


def encabezado_html(p: Proyecto, titulo_documento: str = "", usar_logo=True) -> str:
    logo = (f'<img src="{LOGO_RESOURCE}" width="64" height="64">'
            if usar_logo and p.mostrar_logo and p.logo_path else "")
    anio = (f'<div style="text-align:center;font-style:italic;font-size:8pt;color:#444">'
            f'"{_e(p.denominacion_anio)}"</div>' if p.denominacion_anio else "")
    extra = (f'<div style="font-size:8pt;color:#444">{_e(p.encabezado_extra)}</div>'
             if p.encabezado_extra else "")
    cui = f" &nbsp;|&nbsp; CUI: {_e(p.cui)}" if p.cui else ""
    titulo = (f'<div style="text-align:center;font-size:12pt;font-weight:bold;margin-top:6px">'
              f'{_e(titulo_documento)}</div>' if titulo_documento else "")
    return f"""
{anio}
<table width="100%" cellspacing="0" cellpadding="2" style="border-bottom:1.5px solid #0f2a44">
<tr>
  <td width="70" valign="middle">{logo}</td>
  <td valign="middle">
    <div style="font-size:11pt;font-weight:bold">{_e(p.razon_social)}</div>
    <div style="font-size:8pt">RUC: {_e(p.ruc)}{cui}</div>
    <div style="font-size:8.5pt"><b>Obra:</b> {_e(p.nombre_obra)}</div>
    <div style="font-size:8pt"><b>Ubicación:</b> {_e(p.ubicacion) or '—'}</div>
    {extra}
  </td>
</tr>
</table>
{titulo}"""


def firmas_html(p: Proyecto) -> str:
    activos = [("ALMACENERO", p.firma_almacenero), ("RESIDENTE", p.firma_residente),
               ("SUPERVISOR", p.firma_supervisor)]
    celdas = []
    for rol, mostrar in activos:
        if not mostrar:
            continue
        r = p.responsable(rol)
        detalle = " ".join(x for x in (r.profesion, r.colegiatura) if x)
        celdas.append(
            f'<td align="center" style="font-size:8pt;padding-top:40px">'
            f'______________________________<br><b>{_e(r.nombre) or "&nbsp;"}</b><br>'
            f'{_e(ROLES[rol])}<br>{_e(detalle)}</td>')
    if not celdas:
        return ""
    return f'<table width="100%" style="margin-top:30px"><tr>{"".join(celdas)}</tr></table>'


def pie_html(p: Proyecto) -> str:
    if not p.pie_reporte:
        return ""
    return f'<div style="font-size:7.5pt;color:#555;margin-top:12px;text-align:center">{_e(p.pie_reporte)}</div>'


def ficha_html(p: Proyecto, avance=None) -> str:
    """Ficha de Datos Generales del Proyecto (exportable/imprimible)."""
    def fila(etq, val):
        return (f'<tr><td width="34%" style="background:#eef2f7"><b>{etq}</b></td>'
                f'<td>{_e(str(val)) if val not in (None, "") else "—"}</td></tr>')

    def seccion(titulo, filas):
        return (f'<div style="font-size:10pt;font-weight:bold;color:#0f2a44;margin-top:10px">{titulo}</div>'
                f'<table width="100%" cellspacing="0" cellpadding="3" border="1" '
                f'style="border-color:#b8c4d3;font-size:8.5pt">{"".join(filas)}</table>')

    moneda = MONEDAS.get(p.moneda_codigo, (p.moneda_simbolo, p.moneda_codigo))[1]
    secciones = [
        seccion("1. Empresa / Entidad", [
            fila("Tipo", TIPOS_ENTIDAD.get(p.tipo_entidad)), fila("Razón social", p.razon_social),
            fila("RUC", p.ruc), fila("Dirección", p.direccion),
            fila("Teléfono", p.telefono), fila("Correo", p.correo)]),
        seccion("2. Obra", [
            fila("Nombre de la obra", p.nombre_obra), fila("Nombre corto", p.nombre_corto),
            fila("CUI", p.cui), fila("Modalidad de ejecución", MODALIDADES.get(p.modalidad)),
            *( [fila("Contratista", p.contratista), fila("RUC contratista", p.contratista_ruc),
                fila("N° de contrato", p.numero_contrato)] if p.modalidad == "CONTRATA" else []),
            fila("Fuente de financiamiento", p.fuente_financiamiento),
            fila("Presupuesto", _monto(p)), fila("Moneda", f"{moneda} ({p.moneda_simbolo})"),
            fila("Estado", ESTADOS.get(p.estado))]),
        seccion("3. Ubicación", [
            fila("Departamento", p.departamento), fila("Provincia", p.provincia),
            fila("Distrito", p.distrito), fila("Localidad / dirección de obra", p.localidad)]),
        seccion("4. Responsables", [
            fila(ROLES[rol], " · ".join(x for x in (r.nombre, r.profesion, r.colegiatura,
                                                     f"DNI {r.dni}" if r.dni else "", r.telefono, r.correo) if x))
            for rol in ROLES for r in [p.responsable(rol)]]),
        seccion("5. Plazos", [
            fila("Entrega de terreno", _fecha(p.fecha_entrega_terreno)),
            fila("Inicio de obra", _fecha(p.fecha_inicio)),
            fila("Plazo de ejecución", f"{p.plazo_dias} días calendario" if p.plazo_dias else ""),
            fila("Término programado", _fecha(p.fecha_termino_prog)),
            fila("Término real", _fecha(p.fecha_termino_real)),
            *([fila("Avance temporal al " + date.today().strftime("%d/%m/%Y"),
                    f"{avance[0]} de {avance[1]} días ({avance[2]} %)")] if avance else [])]),
    ]
    return (f'<html><body style="font-family:Arial">{encabezado_html(p, "FICHA DE DATOS GENERALES DEL PROYECTO")}'
            f'{"".join(secciones)}{firmas_html(p)}{pie_html(p)}</body></html>')
