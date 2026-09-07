"""Toma y consulta de pedidos (rol cajero y administrador)."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.servicios import pedidos as servicio_pedidos
from app.servicios.menu import pizzas_disponibles
from app.utilidades import ErrorDeNegocio, requiere_rol

bp = Blueprint("pedidos", __name__, url_prefix="/pedidos")


@bp.route("/")
@requiere_rol("administrador", "cajero")
def listar():
    """Lista los pedidos con filtros por estado, modalidad y busqueda."""
    from app import obtener_bd

    estado = request.args.get("estado", "")
    modalidad = request.args.get("modalidad", "")
    busqueda = request.args.get("busqueda", "").strip()

    return render_template(
        "pedidos_lista.html",
        titulo="Pedidos",
        pedidos=servicio_pedidos.listar_pedidos(obtener_bd(), estado, modalidad, busqueda),
        estado=estado,
        modalidad=modalidad,
        busqueda=busqueda,
    )


@bp.route("/nuevo", methods=["GET", "POST"])
@requiere_rol("administrador", "cajero")
def nuevo():
    """Formulario para registrar un pedido nuevo."""
    from app import obtener_bd

    conexion = obtener_bd()

    if request.method == "POST":
        try:
            pedido_id = servicio_pedidos.crear_pedido(
                conexion,
                modalidad=request.form.get("modalidad", ""),
                cliente=request.form.get("cliente", ""),
                referencia=request.form.get("referencia", ""),
                notas=request.form.get("notas", ""),
                usuario_id=session.get("usuario_id"),
                lineas=_leer_lineas_del_formulario(),
            )
            flash("Pedido registrado. El inventario ya fue descontado.", "exito")
            return redirect(url_for("pedidos.detalle", pedido_id=pedido_id))
        except ErrorDeNegocio as error:
            # La venta se bloquea y se le explica al cajero que insumo falta.
            flash(str(error), "error")

    return render_template(
        "pedido_nuevo.html",
        titulo="Nuevo pedido",
        menu=pizzas_disponibles(conexion),
        formulario=request.form,
    )


def _leer_lineas_del_formulario() -> list:
    """Convierte los campos del formulario en la lista de lineas del pedido.

    El formulario envia tres listas paralelas (pizza_id, tamano y cantidad);
    se ignoran las filas con cantidad cero para que el cajero pueda dejar
    pizzas sin pedir.
    """
    lineas = []
    pizzas = request.form.getlist("pizza_id")
    tamanos = request.form.getlist("tamano")
    cantidades = request.form.getlist("cantidad")

    for pizza_id, tamano, cantidad in zip(pizzas, tamanos, cantidades):
        try:
            unidades = int(cantidad or 0)
        except ValueError:
            unidades = 0
        if unidades > 0:
            lineas.append({"pizza_id": int(pizza_id), "tamano": tamano, "cantidad": unidades})
    return lineas


@bp.route("/<int:pedido_id>")
@requiere_rol("administrador", "cajero")
def detalle(pedido_id):
    """Factura del pedido con sus lineas y su estado."""
    from app import obtener_bd

    pedido = servicio_pedidos.obtener_pedido(obtener_bd(), pedido_id)
    if pedido is None:
        flash("El pedido no existe.", "error")
        return redirect(url_for("pedidos.listar"))

    return render_template("pedido_detalle.html", titulo=f"Pedido {pedido.codigo}", pedido=pedido)


@bp.route("/<int:pedido_id>/estado", methods=["POST"])
@requiere_rol("administrador", "cajero")
def cambiar_estado(pedido_id):
    """Cambia el estado del pedido desde la pantalla de detalle."""
    from app import obtener_bd

    try:
        servicio_pedidos.cambiar_estado(obtener_bd(), pedido_id, request.form.get("estado", ""))
        flash("Estado del pedido actualizado.", "exito")
    except ErrorDeNegocio as error:
        flash(str(error), "error")

    return redirect(url_for("pedidos.detalle", pedido_id=pedido_id))
