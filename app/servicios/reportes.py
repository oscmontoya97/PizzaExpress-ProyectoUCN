"""Reportes basicos de ventas.

Los pedidos cancelados no cuentan como venta, por eso se excluyen de todos los
calculos de este modulo.
"""

from datetime import date, timedelta

from app.configuracion import MODALIDADES, TAMANOS
from app.servicios.inventario import valor_del_inventario

# Condicion que se repite en todas las consultas: solo pedidos vendidos.
SOLO_VENTAS = "p.estado <> 'cancelado'"


def rango_por_defecto() -> tuple:
    """Ultimos 30 dias, que es el rango que se muestra al abrir el reporte."""
    hasta = date.today()
    desde = hasta - timedelta(days=29)
    return (desde.isoformat(), hasta.isoformat())


def _filtro_fechas(desde: str, hasta: str) -> tuple:
    """Fragmento SQL y parametros para filtrar por rango de fechas."""
    # date(creado_en) recorta la hora para poder comparar solo el dia.
    return (" AND date(p.creado_en) BETWEEN ? AND ?", [desde, hasta])


def resumen_de_ventas(conexion, desde: str, hasta: str) -> dict:
    """Totales generales del periodo: ventas, numero de pedidos y ticket promedio."""
    condicion, parametros = _filtro_fechas(desde, hasta)
    fila = conexion.execute(
        f"""SELECT COUNT(*) AS pedidos, COALESCE(SUM(p.total), 0) AS ventas
            FROM pedido p WHERE {SOLO_VENTAS}{condicion}""",
        parametros,
    ).fetchone()

    pizzas = conexion.execute(
        f"""SELECT COALESCE(SUM(d.cantidad), 0)
            FROM detalle_pedido d
            JOIN pedido p ON p.id = d.pedido_id
            WHERE {SOLO_VENTAS}{condicion}""",
        parametros,
    ).fetchone()[0]

    cancelados = conexion.execute(
        """SELECT COUNT(*) FROM pedido p
           WHERE p.estado = 'cancelado' AND date(p.creado_en) BETWEEN ? AND ?""",
        [desde, hasta],
    ).fetchone()[0]

    pedidos = fila["pedidos"]
    ventas = fila["ventas"]
    return {
        "pedidos": pedidos,
        "ventas": ventas,
        "pizzas": pizzas,
        "cancelados": cancelados,
        "ticket_promedio": (ventas / pedidos) if pedidos else 0,
    }


def ventas_por_dia(conexion, desde: str, hasta: str) -> list:
    """Ventas agrupadas por dia, de la mas reciente a la mas antigua."""
    condicion, parametros = _filtro_fechas(desde, hasta)
    filas = conexion.execute(
        f"""SELECT date(p.creado_en) AS dia, COUNT(*) AS pedidos,
                   COALESCE(SUM(p.total), 0) AS ventas
            FROM pedido p
            WHERE {SOLO_VENTAS}{condicion}
            GROUP BY dia
            ORDER BY dia DESC""",
        parametros,
    ).fetchall()
    return [{"dia": f["dia"], "pedidos": f["pedidos"], "ventas": f["ventas"]} for f in filas]


def ventas_por_modalidad(conexion, desde: str, hasta: str) -> list:
    """Cuanto se vendio en mesa, para llevar y a domicilio."""
    condicion, parametros = _filtro_fechas(desde, hasta)
    filas = conexion.execute(
        f"""SELECT p.modalidad, COUNT(*) AS pedidos, COALESCE(SUM(p.total), 0) AS ventas
            FROM pedido p
            WHERE {SOLO_VENTAS}{condicion}
            GROUP BY p.modalidad""",
        parametros,
    ).fetchall()

    encontrados = {f["modalidad"]: f for f in filas}
    total_ventas = sum(f["ventas"] for f in filas) or 1  # evita dividir entre cero

    resultado = []
    for clave, datos in MODALIDADES.items():
        fila = encontrados.get(clave)
        ventas = fila["ventas"] if fila else 0
        resultado.append({
            "modalidad": clave,
            "etiqueta": datos["etiqueta"],
            "pedidos": fila["pedidos"] if fila else 0,
            "ventas": ventas,
            "porcentaje": round(ventas * 100 / total_ventas, 1),
        })
    return resultado


def pizzas_mas_vendidas(conexion, desde: str, hasta: str, limite: int = 10) -> list:
    """Ranking de pizzas por unidades vendidas en el periodo."""
    condicion, parametros = _filtro_fechas(desde, hasta)
    filas = conexion.execute(
        f"""SELECT z.nombre, SUM(d.cantidad) AS unidades,
                   SUM(d.cantidad * d.precio_unitario) AS ventas
            FROM detalle_pedido d
            JOIN pedido p ON p.id = d.pedido_id
            JOIN pizza z ON z.id = d.pizza_id
            WHERE {SOLO_VENTAS}{condicion}
            GROUP BY z.id
            ORDER BY unidades DESC, ventas DESC
            LIMIT ?""",
        parametros + [limite],
    ).fetchall()
    return [{"nombre": f["nombre"], "unidades": f["unidades"], "ventas": f["ventas"]}
            for f in filas]


def ventas_por_tamano(conexion, desde: str, hasta: str) -> list:
    """Cuantas pizzas se vendieron de cada tamano."""
    condicion, parametros = _filtro_fechas(desde, hasta)
    filas = conexion.execute(
        f"""SELECT d.tamano, SUM(d.cantidad) AS unidades,
                   SUM(d.cantidad * d.precio_unitario) AS ventas
            FROM detalle_pedido d
            JOIN pedido p ON p.id = d.pedido_id
            WHERE {SOLO_VENTAS}{condicion}
            GROUP BY d.tamano""",
        parametros,
    ).fetchall()

    encontrados = {f["tamano"]: f for f in filas}
    return [
        {
            "tamano": clave,
            "etiqueta": datos["etiqueta"],
            "unidades": encontrados[clave]["unidades"] if clave in encontrados else 0,
            "ventas": encontrados[clave]["ventas"] if clave in encontrados else 0,
        }
        for clave, datos in TAMANOS.items()
    ]


def reporte_completo(conexion, desde: str, hasta: str) -> dict:
    """Reune todos los bloques del reporte de ventas en un solo diccionario."""
    return {
        "desde": desde,
        "hasta": hasta,
        "resumen": resumen_de_ventas(conexion, desde, hasta),
        "por_dia": ventas_por_dia(conexion, desde, hasta),
        "por_modalidad": ventas_por_modalidad(conexion, desde, hasta),
        "por_tamano": ventas_por_tamano(conexion, desde, hasta),
        "ranking": pizzas_mas_vendidas(conexion, desde, hasta),
        "valor_inventario": valor_del_inventario(conexion),
    }
