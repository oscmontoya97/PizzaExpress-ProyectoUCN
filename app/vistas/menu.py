"""Menu de pizzas: catalogo, recetas y precios."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.servicios import menu as servicio_menu
from app.utilidades import ErrorDeNegocio, requiere_rol

bp = Blueprint("menu", __name__, url_prefix="/menu")


@bp.route("/")
@requiere_rol("administrador", "cajero", "pizzero")
def catalogo():
    """Muestra las pizzas, su receta, sus precios y si se pueden preparar."""
    from app import obtener_bd

    return render_template(
        "menu.html",
        titulo="Menú",
        menu=servicio_menu.pizzas_disponibles(obtener_bd()),
        todas=servicio_menu.listar_pizzas(obtener_bd(), solo_activas=False, con_receta=True),
    )


@bp.route("/<int:pizza_id>/precio", methods=["POST"])
@requiere_rol("administrador")
def cambiar_precio(pizza_id):
    """Actualiza el precio base (tamano mediano) de una pizza."""
    from app import obtener_bd

    valor = (request.form.get("precio_base", "") or "").replace(",", ".").strip()
    try:
        servicio_menu.actualizar_precio(obtener_bd(), pizza_id, float(valor))
        flash("Precio actualizado.", "exito")
    except ValueError:
        flash("El precio debe ser un número.", "error")
    except ErrorDeNegocio as error:
        flash(str(error), "error")

    return redirect(url_for("menu.catalogo"))


@bp.route("/<int:pizza_id>/disponibilidad", methods=["POST"])
@requiere_rol("administrador")
def cambiar_disponibilidad(pizza_id):
    """Activa o retira una pizza del menu."""
    from app import obtener_bd

    activa = request.form.get("activa") == "1"
    servicio_menu.cambiar_disponibilidad(obtener_bd(), pizza_id, activa)
    flash("Pizza activada en el menú." if activa else "Pizza retirada del menú.", "exito")
    return redirect(url_for("menu.catalogo"))
