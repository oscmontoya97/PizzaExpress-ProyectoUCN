"""Reglas de negocio del inventario.

Aqui viven las tres reglas mas importantes del proyecto:
  * calcular cuanto insumo consume un pedido (segun la receta de cada pizza),
  * bloquear la venta cuando falta un insumo,
  * descontar y devolver el stock automaticamente.
"""

from app.configuracion import TAMANOS
from app.modelos import Ingrediente
from app.utilidades import ErrorDeNegocio, formato_cantidad


def listar_ingredientes(conexion, busqueda: str = "", categoria: str = "") -> list:
    """Devuelve los ingredientes del inventario, con filtros opcionales."""
    sql = "SELECT * FROM ingrediente WHERE 1 = 1"
    parametros = []
    if busqueda:
        sql += " AND nombre LIKE ?"
        parametros.append(f"%{busqueda}%")
    if categoria:
        sql += " AND categoria = ?"
        parametros.append(categoria)
    sql += " ORDER BY nombre"
    return [Ingrediente.desde_fila(fila) for fila in conexion.execute(sql, parametros)]


def obtener_ingrediente(conexion, ingrediente_id: int):
    """Devuelve un ingrediente por su id, o None si no existe."""
    fila = conexion.execute(
        "SELECT * FROM ingrediente WHERE id = ?", (ingrediente_id,)
    ).fetchone()
    return Ingrediente.desde_fila(fila) if fila else None


def listar_categorias(conexion) -> list:
    """Categorias distintas presentes en el inventario, para los filtros."""
    return [fila["categoria"] for fila in conexion.execute(
        "SELECT DISTINCT categoria FROM ingrediente ORDER BY categoria")]


def calcular_consumo(conexion, lineas: list) -> dict:
    """Calcula cuanto se gasta de cada ingrediente al preparar unas lineas de pedido.

    Cada linea es un diccionario {pizza_id, tamano, cantidad}. Se suma la receta
    de cada pizza multiplicada por la cantidad pedida y por el factor del tamano,
    porque varias pizzas distintas pueden compartir ingredientes.

    Devuelve un diccionario {ingrediente_id: cantidad_total_consumida}.
    """
    consumo = {}
    for linea in lineas:
        factor = TAMANOS[linea["tamano"]]["factor"]
        filas = conexion.execute(
            "SELECT ingrediente_id, cantidad FROM receta WHERE pizza_id = ?",
            (linea["pizza_id"],),
        ).fetchall()
        if not filas:
            raise ErrorDeNegocio(
                "La pizza seleccionada no tiene receta registrada, no se puede vender."
            )
        for fila in filas:
            requerido = fila["cantidad"] * linea["cantidad"] * factor
            consumo[fila["ingrediente_id"]] = consumo.get(fila["ingrediente_id"], 0) + requerido
    return consumo


def verificar_disponibilidad(conexion, lineas: list):
    """Comprueba si hay inventario suficiente para preparar el pedido.

    Devuelve (hay_stock, faltantes) donde faltantes es una lista de mensajes
    explicando que insumo falta y cuanto. Es la regla que bloquea la venta
    cuando falta un insumo clave.
    """
    consumo = calcular_consumo(conexion, lineas)
    faltantes = []
    for ingrediente_id, requerido in consumo.items():
        ingrediente = obtener_ingrediente(conexion, ingrediente_id)
        if ingrediente is None:
            faltantes.append("Un ingrediente de la receta ya no existe en el inventario.")
            continue
        if ingrediente.stock < requerido:
            faltantes.append(
                "Falta «{}»: se necesitan {} {} y solo hay {} {}.".format(
                    ingrediente.nombre,
                    formato_cantidad(requerido),
                    ingrediente.unidad,
                    formato_cantidad(ingrediente.stock),
                    ingrediente.unidad,
                )
            )
    return (len(faltantes) == 0, faltantes)


def descontar_receta(conexion, lineas: list) -> None:
    """Descuenta del inventario los insumos que consume el pedido.

    No hace commit: quien la llama decide cuando confirmar la transaccion.
    """
    for ingrediente_id, cantidad in calcular_consumo(conexion, lineas).items():
        conexion.execute(
            "UPDATE ingrediente SET stock = stock - ? WHERE id = ?",
            (cantidad, ingrediente_id),
        )


def devolver_receta(conexion, lineas: list) -> None:
    """Devuelve al inventario los insumos de un pedido cancelado."""
    for ingrediente_id, cantidad in calcular_consumo(conexion, lineas).items():
        conexion.execute(
            "UPDATE ingrediente SET stock = stock + ? WHERE id = ?",
            (cantidad, ingrediente_id),
        )


def obtener_alertas(conexion) -> dict:
    """Ingredientes que alcanzaron el stock minimo.

    Separa los que ya estan agotados (stock 0) de los que estan por acabarse.
    """
    ingredientes = [
        Ingrediente.desde_fila(fila)
        for fila in conexion.execute(
            "SELECT * FROM ingrediente WHERE stock <= stock_minimo ORDER BY stock, nombre")
    ]
    agotados = [i for i in ingredientes if i.esta_agotado]
    bajos = [i for i in ingredientes if i.esta_bajo]
    return {
        "agotados": agotados,
        "bajos": bajos,
        "todas": ingredientes,
        "total": len(ingredientes),
    }


def contar_alertas(conexion) -> int:
    """Numero de ingredientes en alerta (para el distintivo del menu)."""
    return conexion.execute(
        "SELECT COUNT(*) FROM ingrediente WHERE stock <= stock_minimo").fetchone()[0]


def reabastecer(conexion, ingrediente_id: int, cantidad: float) -> None:
    """Suma una cantidad al stock de un ingrediente (llegada de un proveedor)."""
    if cantidad <= 0:
        raise ErrorDeNegocio("La cantidad a reabastecer debe ser mayor que cero.")
    if obtener_ingrediente(conexion, ingrediente_id) is None:
        raise ErrorDeNegocio("El ingrediente no existe.")
    conexion.execute(
        "UPDATE ingrediente SET stock = stock + ? WHERE id = ?", (cantidad, ingrediente_id))
    conexion.commit()


def guardar_ingrediente(conexion, datos: dict, ingrediente_id=None) -> None:
    """Crea un ingrediente nuevo o actualiza uno existente."""
    if not datos["nombre"].strip():
        raise ErrorDeNegocio("El nombre del ingrediente es obligatorio.")
    if datos["stock"] < 0 or datos["stock_minimo"] < 0 or datos["costo_unitario"] < 0:
        raise ErrorDeNegocio("Las cantidades y el costo no pueden ser negativos.")

    try:
        if ingrediente_id is None:
            conexion.execute(
                """INSERT INTO ingrediente
                   (nombre, categoria, unidad, stock, stock_minimo, costo_unitario)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (datos["nombre"].strip(), datos["categoria"], datos["unidad"],
                 datos["stock"], datos["stock_minimo"], datos["costo_unitario"]),
            )
        else:
            conexion.execute(
                """UPDATE ingrediente
                   SET nombre = ?, categoria = ?, unidad = ?, stock = ?,
                       stock_minimo = ?, costo_unitario = ?
                   WHERE id = ?""",
                (datos["nombre"].strip(), datos["categoria"], datos["unidad"],
                 datos["stock"], datos["stock_minimo"], datos["costo_unitario"],
                 ingrediente_id),
            )
        conexion.commit()
    except Exception as error:
        conexion.rollback()
        if "UNIQUE" in str(error):
            raise ErrorDeNegocio("Ya existe un ingrediente con ese nombre.")
        raise


def valor_del_inventario(conexion) -> float:
    """Suma del stock por su costo unitario: cuanto dinero hay guardado en la bodega."""
    total = conexion.execute(
        "SELECT COALESCE(SUM(stock * costo_unitario), 0) FROM ingrediente").fetchone()[0]
    return total or 0.0
