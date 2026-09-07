"""Panel de inicio: resumen del dia para cualquier rol."""

from datetime import date

from flask import Blueprint, render_template

from app.servicios import inventario as servicio_inventario
from app.servicios import pedidos as servicio_pedidos
from app.servicios import reportes as servicio_reportes
from app.utilidades import requiere_sesion

bp = Blueprint("panel", __name__)


@bp.route("/")
@requiere_sesion
def inicio():
    """Muestra las metricas principales y los ultimos pedidos."""
    from app import obtener_bd

    conexion = obtener_bd()
    hoy = date.today().isoformat()

    return render_template(
        "panel.html",
        titulo="Panel",
        resumen_hoy=servicio_reportes.resumen_de_ventas(conexion, hoy, hoy),
        alertas=servicio_inventario.obtener_alertas(conexion),
        valor_inventario=servicio_inventario.valor_del_inventario(conexion),
        pedidos_activos=servicio_pedidos.contar_pedidos_activos(conexion),
        ultimos_pedidos=servicio_pedidos.listar_pedidos(conexion)[:5],
    )
