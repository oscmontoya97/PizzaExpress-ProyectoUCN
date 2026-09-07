"""Pruebas de la logica de negocio de Pizza Express.

Se usa unittest, que viene con Python, y una base de datos en memoria: las
pruebas no tocan los datos reales de la aplicacion.

Ejecutar con:  python -m unittest discover -s pruebas -v
"""

import os
import sqlite3
import sys
import unittest

# Permite ejecutar las pruebas desde la raiz del proyecto.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.basedatos import ESQUEMA, sembrar_datos            # noqa: E402
from app.servicios import inventario as servicio_inventario  # noqa: E402
from app.servicios import pedidos as servicio_pedidos        # noqa: E402
from app.servicios import reportes as servicio_reportes      # noqa: E402
from app.servicios.autenticacion import validar_credenciales  # noqa: E402
from app.utilidades import ErrorDeNegocio                     # noqa: E402


class PruebaBase(unittest.TestCase):
    """Crea una base de datos nueva en memoria antes de cada prueba."""

    def setUp(self):
        self.conexion = sqlite3.connect(":memory:")
        self.conexion.row_factory = sqlite3.Row
        self.conexion.executescript(ESQUEMA)
        sembrar_datos(self.conexion)

        # Atajos que usan casi todas las pruebas.
        self.pizzas = {fila["nombre"]: fila["id"]
                       for fila in self.conexion.execute("SELECT id, nombre FROM pizza")}
        self.cajero_id = self.conexion.execute(
            "SELECT id FROM usuario WHERE usuario = 'cajero'").fetchone()["id"]

    def tearDown(self):
        self.conexion.close()

    def stock_de(self, nombre):
        """Devuelve el stock actual de un ingrediente por su nombre."""
        return self.conexion.execute(
            "SELECT stock FROM ingrediente WHERE nombre = ?", (nombre,)).fetchone()["stock"]


class PruebasDeInventario(PruebaBase):
    """Descuento automatico, alertas y reabastecimiento."""

    def test_el_consumo_suma_los_ingredientes_compartidos(self):
        """Dos pizzas que usan harina deben sumar su consumo en un solo total."""
        lineas = [
            {"pizza_id": self.pizzas["Margarita"], "tamano": "mediana", "cantidad": 1},
            {"pizza_id": self.pizzas["Pepperoni"], "tamano": "mediana", "cantidad": 1},
        ]
        consumo = servicio_inventario.calcular_consumo(self.conexion, lineas)
        id_harina = self.conexion.execute(
            "SELECT id FROM ingrediente WHERE nombre = 'Harina de trigo'").fetchone()["id"]
        # Cada pizza mediana lleva 0.30 kg de harina.
        self.assertAlmostEqual(consumo[id_harina], 0.60)

    def test_el_tamano_multiplica_el_consumo(self):
        """Una pizza familiar consume 1.6 veces lo de una mediana."""
        def consumo_de(tamano):
            lineas = [{"pizza_id": self.pizzas["Margarita"], "tamano": tamano, "cantidad": 1}]
            return sum(servicio_inventario.calcular_consumo(self.conexion, lineas).values())

        self.assertAlmostEqual(consumo_de("familiar"), consumo_de("mediana") * 1.6)

    def test_las_alertas_separan_agotados_de_bajos(self):
        """El queso azul empieza en cero y debe salir como agotado."""
        alertas = servicio_inventario.obtener_alertas(self.conexion)
        nombres_agotados = [i.nombre for i in alertas["agotados"]]
        self.assertIn("Queso azul", nombres_agotados)
        # Ningun ingrediente puede estar en las dos listas a la vez.
        self.assertEqual(
            set(i.nombre for i in alertas["agotados"]) & set(i.nombre for i in alertas["bajos"]),
            set(),
        )

    def test_reabastecer_suma_al_stock(self):
        id_azul = self.conexion.execute(
            "SELECT id FROM ingrediente WHERE nombre = 'Queso azul'").fetchone()["id"]
        servicio_inventario.reabastecer(self.conexion, id_azul, 3)
        self.assertAlmostEqual(self.stock_de("Queso azul"), 3)

    def test_no_se_puede_reabastecer_una_cantidad_negativa(self):
        id_azul = self.conexion.execute(
            "SELECT id FROM ingrediente WHERE nombre = 'Queso azul'").fetchone()["id"]
        with self.assertRaises(ErrorDeNegocio):
            servicio_inventario.reabastecer(self.conexion, id_azul, -5)


class PruebasDePedidos(PruebaBase):
    """Creacion de pedidos, bloqueo de venta y ciclo de estados."""

    def crear_pedido_simple(self, pizza="Margarita", tamano="mediana", cantidad=1,
                            modalidad="mesa", referencia="Mesa 1"):
        return servicio_pedidos.crear_pedido(
            self.conexion,
            modalidad=modalidad,
            cliente="Cliente de prueba",
            referencia=referencia,
            notas="",
            usuario_id=self.cajero_id,
            lineas=[{"pizza_id": self.pizzas[pizza], "tamano": tamano, "cantidad": cantidad}],
        )

    def test_crear_un_pedido_descuenta_el_inventario(self):
        antes = self.stock_de("Queso mozzarella")
        self.crear_pedido_simple()
        # Una Margarita mediana lleva 0.25 kg de mozzarella.
        self.assertAlmostEqual(self.stock_de("Queso mozzarella"), antes - 0.25)

    def test_el_total_usa_el_precio_del_tamano(self):
        pedido_id = self.crear_pedido_simple(tamano="familiar")
        pedido = servicio_pedidos.obtener_pedido(self.conexion, pedido_id)
        # Margarita mediana cuesta 28000; la familiar 28000 * 1.6 = 44800.
        self.assertEqual(pedido.total, 44800)

    def test_se_bloquea_la_venta_si_falta_un_insumo(self):
        """La Cuatro Quesos no se puede vender porque el queso azul esta agotado."""
        with self.assertRaises(ErrorDeNegocio) as contexto:
            self.crear_pedido_simple(pizza="Cuatro Quesos")
        self.assertIn("Queso azul", str(contexto.exception))

    def test_una_venta_bloqueada_no_toca_el_inventario(self):
        antes = self.stock_de("Queso parmesano")
        with self.assertRaises(ErrorDeNegocio):
            self.crear_pedido_simple(pizza="Cuatro Quesos")
        self.assertAlmostEqual(self.stock_de("Queso parmesano"), antes)

    def test_el_domicilio_exige_direccion(self):
        with self.assertRaises(ErrorDeNegocio):
            self.crear_pedido_simple(modalidad="domicilio", referencia="")

    def test_un_pedido_sin_pizzas_se_rechaza(self):
        with self.assertRaises(ErrorDeNegocio):
            servicio_pedidos.crear_pedido(
                self.conexion, modalidad="mesa", cliente="Cliente", referencia="Mesa 2",
                notas="", usuario_id=self.cajero_id, lineas=[])

    def test_el_ciclo_de_estados_avanza_en_orden(self):
        pedido_id = self.crear_pedido_simple()
        for estado in ["en_preparacion", "lista", "entregado"]:
            servicio_pedidos.cambiar_estado(self.conexion, pedido_id, estado)
        pedido = servicio_pedidos.obtener_pedido(self.conexion, pedido_id)
        self.assertEqual(pedido.estado, "entregado")

    def test_no_se_puede_saltar_un_estado(self):
        pedido_id = self.crear_pedido_simple()
        with self.assertRaises(ErrorDeNegocio):
            servicio_pedidos.cambiar_estado(self.conexion, pedido_id, "entregado")

    def test_cancelar_devuelve_los_ingredientes(self):
        antes = self.stock_de("Queso mozzarella")
        pedido_id = self.crear_pedido_simple()
        servicio_pedidos.cambiar_estado(self.conexion, pedido_id, "cancelado")
        self.assertAlmostEqual(self.stock_de("Queso mozzarella"), antes)

    def test_un_pedido_entregado_ya_no_se_puede_cancelar(self):
        pedido_id = self.crear_pedido_simple()
        for estado in ["en_preparacion", "lista", "entregado"]:
            servicio_pedidos.cambiar_estado(self.conexion, pedido_id, estado)
        with self.assertRaises(ErrorDeNegocio):
            servicio_pedidos.cambiar_estado(self.conexion, pedido_id, "cancelado")


class PruebasDeReportes(PruebaBase):
    """Los reportes no deben contar los pedidos cancelados."""

    def test_un_pedido_cancelado_no_cuenta_como_venta(self):
        rango = ("2000-01-01", "2100-12-31")
        antes = servicio_reportes.resumen_de_ventas(self.conexion, *rango)

        pedido_id = servicio_pedidos.crear_pedido(
            self.conexion, modalidad="llevar", cliente="Cliente", referencia="",
            notas="", usuario_id=self.cajero_id,
            lineas=[{"pizza_id": self.pizzas["Margarita"], "tamano": "mediana", "cantidad": 1}])
        servicio_pedidos.cambiar_estado(self.conexion, pedido_id, "cancelado")

        despues = servicio_reportes.resumen_de_ventas(self.conexion, *rango)
        self.assertEqual(antes["ventas"], despues["ventas"])
        self.assertEqual(despues["cancelados"], antes["cancelados"] + 1)


class PruebasDeAutenticacion(PruebaBase):
    """Acceso de los empleados."""

    def test_credenciales_correctas(self):
        usuario = validar_credenciales(self.conexion, "admin", "admin123")
        self.assertIsNotNone(usuario)
        self.assertEqual(usuario.rol, "administrador")

    def test_credenciales_incorrectas(self):
        self.assertIsNone(validar_credenciales(self.conexion, "admin", "clave-mala"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
