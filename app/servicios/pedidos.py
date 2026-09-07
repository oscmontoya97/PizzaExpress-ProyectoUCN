"""Reglas de negocio de los pedidos.

Un pedido pasa por los estados pendiente -> en preparacion -> lista -> entregado
y puede cancelarse en cualquier punto antes de la entrega. Al crearlo se descuenta
el inventario y al cancelarlo se devuelve.
"""

from app.configuracion import MODALIDADES, TAMANOS, TRANSICIONES_PERMITIDAS
from app.modelos import LineaDePedido, Pedido
from app.servicios import inventario as servicio_inventario
from app.servicios.menu import obtener_pizza
from app.utilidades import ErrorDeNegocio


def generar_codigo(conexion) -> str:
    """Genera el siguiente codigo legible de pedido: PED-0001, PED-0002..."""
    ultimo = conexion.execute("SELECT MAX(id) FROM pedido").fetchone()[0] or 0
    numero = ultimo + 1
    codigo = f"PED-{numero:04d}"
    # Por seguridad se busca el primer codigo libre (si se borraron pedidos).
    while conexion.execute("SELECT 1 FROM pedido WHERE codigo = ?", (codigo,)).fetchone():
        numero += 1
        codigo = f"PED-{numero:04d}"
    return codigo


def validar_lineas(conexion, lineas: list) -> list:
    """Revisa las lineas del pedido y les agrega el nombre y el precio de la pizza."""
    if not lineas:
        raise ErrorDeNegocio("Agrega al menos una pizza al pedido.")

    lineas_validadas = []
    for linea in lineas:
        if linea["tamano"] not in TAMANOS:
            raise ErrorDeNegocio("El tamaño seleccionado no es válido.")
        if linea["cantidad"] <= 0:
            raise ErrorDeNegocio("La cantidad de pizzas debe ser mayor que cero.")

        pizza = obtener_pizza(conexion, linea["pizza_id"], con_receta=False)
        if pizza is None:
            raise ErrorDeNegocio("Una de las pizzas seleccionadas no existe.")
        if not pizza.activa:
            raise ErrorDeNegocio(f"La pizza «{pizza.nombre}» no está disponible en el menú.")

        lineas_validadas.append({
            "pizza_id": pizza.id,
            "pizza_nombre": pizza.nombre,
            "tamano": linea["tamano"],
            "cantidad": int(linea["cantidad"]),
            "precio_unitario": pizza.precio_por_tamano(linea["tamano"]),
        })
    return lineas_validadas


def crear_pedido(conexion, modalidad, cliente, referencia, notas, usuario_id, lineas) -> int:
    """Registra un pedido nuevo y descuenta el inventario.

    Si falta algun insumo la venta se bloquea: se lanza ErrorDeNegocio y no se
    modifica nada en la base de datos.

    Devuelve el id del pedido creado.
    """
    if modalidad not in MODALIDADES:
        raise ErrorDeNegocio("La modalidad del pedido no es válida.")
    if not cliente.strip():
        raise ErrorDeNegocio("El nombre del cliente es obligatorio.")
    if MODALIDADES[modalidad]["referencia_obligatoria"] and not referencia.strip():
        raise ErrorDeNegocio(
            "Falta el dato «{}» para un pedido {}.".format(
                MODALIDADES[modalidad]["etiqueta_referencia"],
                MODALIDADES[modalidad]["etiqueta"].lower(),
            )
        )

    lineas_validadas = validar_lineas(conexion, lineas)

    # Bloqueo de la venta si falta un insumo clave.
    hay_stock, faltantes = servicio_inventario.verificar_disponibilidad(conexion, lineas_validadas)
    if not hay_stock:
        raise ErrorDeNegocio(
            "No hay inventario suficiente para este pedido. " + " ".join(faltantes))

    total = sum(linea["cantidad"] * linea["precio_unitario"] for linea in lineas_validadas)

    try:
        cursor = conexion.execute(
            """INSERT INTO pedido (codigo, modalidad, cliente, referencia, estado,
                                   total, notas, usuario_id)
               VALUES (?, ?, ?, ?, 'pendiente', ?, ?, ?)""",
            (generar_codigo(conexion), modalidad, cliente.strip(), referencia.strip(),
             total, notas.strip(), usuario_id),
        )
        pedido_id = cursor.lastrowid
        conexion.executemany(
            """INSERT INTO detalle_pedido (pedido_id, pizza_id, tamano, cantidad, precio_unitario)
               VALUES (?, ?, ?, ?, ?)""",
            [(pedido_id, l["pizza_id"], l["tamano"], l["cantidad"], l["precio_unitario"])
             for l in lineas_validadas],
        )
        # Descuento automatico del inventario segun la receta de cada pizza.
        servicio_inventario.descontar_receta(conexion, lineas_validadas)
        conexion.commit()
    except Exception:
        # Si algo falla a mitad de camino se deshace todo el pedido.
        conexion.rollback()
        raise

    return pedido_id


def obtener_lineas(conexion, pedido_id: int) -> list:
    """Lineas de un pedido, con el nombre de la pizza."""
    filas = conexion.execute(
        """SELECT d.id, d.pizza_id, d.tamano, d.cantidad, d.precio_unitario,
                  p.nombre AS pizza_nombre
           FROM detalle_pedido d
           JOIN pizza p ON p.id = d.pizza_id
           WHERE d.pedido_id = ?
           ORDER BY d.id""",
        (pedido_id,),
    ).fetchall()
    return [LineaDePedido.desde_fila(fila) for fila in filas]


def obtener_pedido(conexion, pedido_id: int):
    """Devuelve el pedido completo (cabecera y lineas), o None si no existe."""
    fila = conexion.execute(
        """SELECT p.*, COALESCE(u.nombre, 'Sistema') AS usuario_nombre
           FROM pedido p
           LEFT JOIN usuario u ON u.id = p.usuario_id
           WHERE p.id = ?""",
        (pedido_id,),
    ).fetchone()
    if fila is None:
        return None
    pedido = Pedido.desde_fila(fila)
    pedido.lineas = obtener_lineas(conexion, pedido.id)
    return pedido


def listar_pedidos(conexion, estado: str = "", modalidad: str = "", busqueda: str = "") -> list:
    """Lista los pedidos aplicando los filtros de la pantalla de pedidos."""
    sql = """SELECT p.*, COALESCE(u.nombre, 'Sistema') AS usuario_nombre
             FROM pedido p
             LEFT JOIN usuario u ON u.id = p.usuario_id
             WHERE 1 = 1"""
    parametros = []
    if estado:
        sql += " AND p.estado = ?"
        parametros.append(estado)
    if modalidad:
        sql += " AND p.modalidad = ?"
        parametros.append(modalidad)
    if busqueda:
        sql += " AND (p.codigo LIKE ? OR p.cliente LIKE ?)"
        parametros.extend([f"%{busqueda}%", f"%{busqueda}%"])
    sql += " ORDER BY p.creado_en DESC, p.id DESC"

    pedidos = []
    for fila in conexion.execute(sql, parametros):
        pedido = Pedido.desde_fila(fila)
        pedido.lineas = obtener_lineas(conexion, pedido.id)
        pedidos.append(pedido)
    return pedidos


def pedidos_en_cocina(conexion) -> dict:
    """Pedidos agrupados por estado para el tablero de la cocina."""
    tablero = {"pendiente": [], "en_preparacion": [], "lista": []}
    for pedido in listar_pedidos(conexion):
        if pedido.estado in tablero:
            tablero[pedido.estado].append(pedido)
    return tablero


def cambiar_estado(conexion, pedido_id: int, nuevo_estado: str) -> None:
    """Mueve el pedido a otro estado respetando el ciclo de vida.

    Al cancelar un pedido que ya habia descontado inventario, los insumos se
    devuelven automaticamente a la bodega.
    """
    pedido = obtener_pedido(conexion, pedido_id)
    if pedido is None:
        raise ErrorDeNegocio("El pedido no existe.")
    if nuevo_estado not in TRANSICIONES_PERMITIDAS.get(pedido.estado, []):
        raise ErrorDeNegocio(
            "No se puede pasar de «{}» a «{}».".format(pedido.estado_legible, nuevo_estado))

    try:
        if nuevo_estado == "cancelado":
            lineas = [{"pizza_id": l.pizza_id, "tamano": l.tamano, "cantidad": l.cantidad}
                      for l in pedido.lineas]
            servicio_inventario.devolver_receta(conexion, lineas)
        conexion.execute("UPDATE pedido SET estado = ? WHERE id = ?", (nuevo_estado, pedido_id))
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise


def contar_pedidos_activos(conexion) -> int:
    """Pedidos que todavia estan en el flujo de la cocina."""
    return conexion.execute(
        "SELECT COUNT(*) FROM pedido WHERE estado IN ('pendiente', 'en_preparacion', 'lista')"
    ).fetchone()[0]
