"""Consultas y edicion del menu de pizzas."""

from app.configuracion import TAMANOS
from app.modelos import IngredienteDeReceta, Pizza
from app.servicios.inventario import calcular_consumo, obtener_ingrediente
from app.utilidades import ErrorDeNegocio


def listar_pizzas(conexion, solo_activas: bool = True, con_receta: bool = False) -> list:
    """Devuelve las pizzas del menu, opcionalmente con su receta cargada."""
    sql = "SELECT * FROM pizza"
    if solo_activas:
        sql += " WHERE activa = 1"
    sql += " ORDER BY nombre"

    pizzas = [Pizza.desde_fila(fila) for fila in conexion.execute(sql)]
    if con_receta:
        for pizza in pizzas:
            pizza.receta = obtener_receta(conexion, pizza.id)
    return pizzas


def obtener_pizza(conexion, pizza_id: int, con_receta: bool = True):
    """Devuelve una pizza por su id, o None si no existe."""
    fila = conexion.execute("SELECT * FROM pizza WHERE id = ?", (pizza_id,)).fetchone()
    if fila is None:
        return None
    pizza = Pizza.desde_fila(fila)
    if con_receta:
        pizza.receta = obtener_receta(conexion, pizza.id)
    return pizza


def obtener_receta(conexion, pizza_id: int) -> list:
    """Ingredientes y cantidades que consume una pizza mediana."""
    filas = conexion.execute(
        """SELECT r.ingrediente_id, r.cantidad, i.nombre, i.unidad
           FROM receta r
           JOIN ingrediente i ON i.id = r.ingrediente_id
           WHERE r.pizza_id = ?
           ORDER BY i.nombre""",
        (pizza_id,),
    ).fetchall()
    return [
        IngredienteDeReceta(
            ingrediente_id=fila["ingrediente_id"],
            nombre=fila["nombre"],
            unidad=fila["unidad"],
            cantidad=fila["cantidad"],
        )
        for fila in filas
    ]


def pizzas_disponibles(conexion) -> list:
    """Menu con la informacion de disponibilidad de cada pizza y tamano.

    Para cada pizza se revisa, tamano por tamano, si hay inventario suficiente
    para preparar al menos una. Asi el cajero ve en pantalla que puede vender
    antes de intentar registrar el pedido.
    """
    resultado = []
    for pizza in listar_pizzas(conexion, solo_activas=True, con_receta=True):
        tamanos = {}
        for clave in TAMANOS:
            linea = [{"pizza_id": pizza.id, "tamano": clave, "cantidad": 1}]
            faltantes = []
            for ingrediente_id, requerido in calcular_consumo(conexion, linea).items():
                ingrediente = obtener_ingrediente(conexion, ingrediente_id)
                if ingrediente is None or ingrediente.stock < requerido:
                    faltantes.append(ingrediente.nombre if ingrediente else "ingrediente eliminado")
            tamanos[clave] = {
                "precio": pizza.precio_por_tamano(clave),
                "disponible": len(faltantes) == 0,
                "faltantes": faltantes,
            }
        resultado.append({
            "pizza": pizza,
            "tamanos": tamanos,
            # Una pizza se considera disponible si al menos un tamano se puede preparar.
            "disponible": any(t["disponible"] for t in tamanos.values()),
        })
    return resultado


def actualizar_precio(conexion, pizza_id: int, precio_base: float) -> None:
    """Cambia el precio base (tamano mediano) de una pizza."""
    if precio_base <= 0:
        raise ErrorDeNegocio("El precio debe ser mayor que cero.")
    if obtener_pizza(conexion, pizza_id, con_receta=False) is None:
        raise ErrorDeNegocio("La pizza no existe.")
    conexion.execute("UPDATE pizza SET precio_base = ? WHERE id = ?", (precio_base, pizza_id))
    conexion.commit()


def cambiar_disponibilidad(conexion, pizza_id: int, activa: bool) -> None:
    """Activa o retira una pizza del menu sin borrarla del historial."""
    conexion.execute("UPDATE pizza SET activa = ? WHERE id = ?", (1 if activa else 0, pizza_id))
    conexion.commit()
