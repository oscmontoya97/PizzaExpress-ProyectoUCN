"""Gestion del inventario y alertas de stock minimo."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.servicios import inventario as servicio_inventario
from app.utilidades import ErrorDeNegocio, requiere_rol

bp = Blueprint("inventario", __name__, url_prefix="/inventario")


def _numero(campo: str, por_defecto: float = 0.0) -> float:
    """Lee un numero del formulario tolerando comas y campos vacios."""
    valor = (request.form.get(campo, "") or "").replace(",", ".").strip()
    try:
        return float(valor)
    except ValueError:
        return por_defecto


@bp.route("/")
@requiere_rol("administrador", "cajero")
def listar():
    """Tabla del inventario con buscador y filtro por categoria."""
    from app import obtener_bd

    conexion = obtener_bd()
    busqueda = request.args.get("busqueda", "").strip()
    categoria = request.args.get("categoria", "")

    return render_template(
        "inventario.html",
        titulo="Inventario",
        ingredientes=servicio_inventario.listar_ingredientes(conexion, busqueda, categoria),
        categorias=servicio_inventario.listar_categorias(conexion),
        valor_inventario=servicio_inventario.valor_del_inventario(conexion),
        busqueda=busqueda,
        categoria=categoria,
    )


@bp.route("/alertas")
@requiere_rol("administrador", "cajero", "pizzero")
def alertas():
    """Ingredientes agotados o por debajo del stock minimo."""
    from app import obtener_bd

    return render_template(
        "alertas.html",
        titulo="Alertas de inventario",
        alertas=servicio_inventario.obtener_alertas(obtener_bd()),
    )


@bp.route("/<int:ingrediente_id>/reabastecer", methods=["POST"])
@requiere_rol("administrador")
def reabastecer(ingrediente_id):
    """Suma al stock la cantidad que llego del proveedor."""
    from app import obtener_bd

    try:
        servicio_inventario.reabastecer(obtener_bd(), ingrediente_id, _numero("cantidad"))
        flash("Inventario reabastecido.", "exito")
    except ErrorDeNegocio as error:
        flash(str(error), "error")

    return redirect(request.form.get("volver_a") or url_for("inventario.listar"))


@bp.route("/nuevo", methods=["GET", "POST"])
@bp.route("/<int:ingrediente_id>/editar", methods=["GET", "POST"])
@requiere_rol("administrador")
def guardar(ingrediente_id=None):
    """Formulario para crear o editar un ingrediente."""
    from app import obtener_bd

    conexion = obtener_bd()
    ingrediente = (servicio_inventario.obtener_ingrediente(conexion, ingrediente_id)
                   if ingrediente_id else None)

    if ingrediente_id and ingrediente is None:
        flash("El ingrediente no existe.", "error")
        return redirect(url_for("inventario.listar"))

    if request.method == "POST":
        datos = {
            "nombre": request.form.get("nombre", ""),
            "categoria": request.form.get("categoria", "General").strip() or "General",
            "unidad": request.form.get("unidad", "unidad").strip() or "unidad",
            "stock": _numero("stock"),
            "stock_minimo": _numero("stock_minimo"),
            "costo_unitario": _numero("costo_unitario"),
        }
        try:
            servicio_inventario.guardar_ingrediente(conexion, datos, ingrediente_id)
            flash("Ingrediente guardado.", "exito")
            return redirect(url_for("inventario.listar"))
        except ErrorDeNegocio as error:
            flash(str(error), "error")

    return render_template(
        "ingrediente_formulario.html",
        titulo="Editar ingrediente" if ingrediente else "Nuevo ingrediente",
        ingrediente=ingrediente,
        categorias=servicio_inventario.listar_categorias(conexion),
    )
