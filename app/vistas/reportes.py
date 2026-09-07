"""Reportes basicos de ventas (solo el administrador)."""

from flask import Blueprint, render_template, request

from app.servicios import reportes as servicio_reportes
from app.utilidades import requiere_rol

bp = Blueprint("reportes", __name__, url_prefix="/reportes")


@bp.route("/")
@requiere_rol("administrador")
def ventas():
    """Reporte de ventas del periodo seleccionado."""
    from app import obtener_bd

    desde_defecto, hasta_defecto = servicio_reportes.rango_por_defecto()
    desde = request.args.get("desde") or desde_defecto
    hasta = request.args.get("hasta") or hasta_defecto

    return render_template(
        "reportes.html",
        titulo="Reportes de ventas",
        reporte=servicio_reportes.reporte_completo(obtener_bd(), desde, hasta),
    )
