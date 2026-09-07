"""Tablero de la cocina (rol pizzero y administrador)."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.servicios import pedidos as servicio_pedidos
from app.utilidades import ErrorDeNegocio, requiere_rol

bp = Blueprint("cocina", __name__, url_prefix="/cocina")


@bp.route("/")
@requiere_rol("administrador", "pizzero")
def tablero():
    """Muestra los pedidos agrupados por estado, en columnas."""
    from app import obtener_bd

    return render_template(
        "cocina.html",
        titulo="Cocina",
        tablero=servicio_pedidos.pedidos_en_cocina(obtener_bd()),
    )


@bp.route("/<int:pedido_id>/estado", methods=["POST"])
@requiere_rol("administrador", "pizzero")
def avanzar(pedido_id):
    """Mueve un pedido al siguiente estado desde el tablero."""
    from app import obtener_bd

    try:
        servicio_pedidos.cambiar_estado(obtener_bd(), pedido_id, request.form.get("estado", ""))
        flash("Pedido actualizado.", "exito")
    except ErrorDeNegocio as error:
        flash(str(error), "error")

    return redirect(url_for("cocina.tablero"))
