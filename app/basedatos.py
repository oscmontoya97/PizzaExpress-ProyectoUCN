"""Acceso a la base de datos SQLite y creacion de los datos de ejemplo.

Se usa el modulo sqlite3 de la biblioteca estandar de Python, asi el proyecto
no necesita instalar ningun motor de base de datos ni un ORM.
"""

import hashlib
import sqlite3

from app.configuracion import RUTA_BD, RUTA_DATOS

# Sentencias que crean el esquema. Se ejecutan solo si las tablas no existen.
ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuario (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre     TEXT NOT NULL,
    usuario    TEXT NOT NULL UNIQUE,
    clave_hash TEXT NOT NULL,
    rol        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ingrediente (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre         TEXT NOT NULL UNIQUE,
    categoria      TEXT NOT NULL DEFAULT 'General',
    unidad         TEXT NOT NULL DEFAULT 'unidad',
    stock          REAL NOT NULL DEFAULT 0,
    stock_minimo   REAL NOT NULL DEFAULT 0,
    costo_unitario REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS pizza (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT NOT NULL UNIQUE,
    descripcion TEXT NOT NULL DEFAULT '',
    precio_base REAL NOT NULL DEFAULT 0,
    activa      INTEGER NOT NULL DEFAULT 1
);

-- Receta: que ingredientes y cuanto consume cada pizza (tamano mediano).
-- Es la tabla que permite descontar el inventario automaticamente por pizza.
CREATE TABLE IF NOT EXISTS receta (
    pizza_id       INTEGER NOT NULL REFERENCES pizza(id) ON DELETE CASCADE,
    ingrediente_id INTEGER NOT NULL REFERENCES ingrediente(id) ON DELETE RESTRICT,
    cantidad       REAL NOT NULL,
    PRIMARY KEY (pizza_id, ingrediente_id)
);

CREATE TABLE IF NOT EXISTS pedido (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo     TEXT NOT NULL UNIQUE,
    modalidad  TEXT NOT NULL,
    cliente    TEXT NOT NULL,
    referencia TEXT DEFAULT '',
    estado     TEXT NOT NULL DEFAULT 'pendiente',
    total      REAL NOT NULL DEFAULT 0,
    notas      TEXT DEFAULT '',
    usuario_id INTEGER REFERENCES usuario(id) ON DELETE SET NULL,
    creado_en  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS detalle_pedido (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id       INTEGER NOT NULL REFERENCES pedido(id) ON DELETE CASCADE,
    pizza_id        INTEGER NOT NULL REFERENCES pizza(id) ON DELETE RESTRICT,
    tamano          TEXT NOT NULL,
    cantidad        INTEGER NOT NULL,
    precio_unitario REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pedido_estado ON pedido(estado);
CREATE INDEX IF NOT EXISTS idx_pedido_fecha ON pedido(creado_en);
CREATE INDEX IF NOT EXISTS idx_detalle_pedido ON detalle_pedido(pedido_id);
"""


def cifrar_clave(clave: str) -> str:
    """Devuelve el hash SHA-256 de una clave, para no guardarla en texto plano."""
    return hashlib.sha256(clave.encode("utf-8")).hexdigest()


def obtener_conexion() -> sqlite3.Connection:
    """Abre una conexion a la base de datos SQLite del proyecto."""
    RUTA_DATOS.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(RUTA_BD)
    # sqlite3.Row permite leer las columnas por nombre: fila["nombre"].
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def crear_esquema(conexion: sqlite3.Connection) -> None:
    """Crea las tablas si todavia no existen."""
    conexion.executescript(ESQUEMA)
    conexion.commit()


def inicializar_base_de_datos() -> None:
    """Crea el esquema y, si la base esta vacia, carga los datos de ejemplo."""
    conexion = obtener_conexion()
    try:
        crear_esquema(conexion)
        if conexion.execute("SELECT COUNT(*) FROM usuario").fetchone()[0] == 0:
            sembrar_datos(conexion)
            print("Base de datos creada y poblada con datos de ejemplo.")
    finally:
        conexion.close()


# ---------------------------------------------------------------------------
# Datos de ejemplo
# ---------------------------------------------------------------------------

# Usuarios de prueba: uno por cada rol descrito en el proyecto.
# El nombre es generico (Administrador, Cajero, Pizzero) para que la aplicacion
# no dependa de quien la opere.
USUARIOS_INICIALES = [
    ("Administrador", "admin", "admin123", "administrador"),
    ("Cajero", "cajero", "cajero123", "cajero"),
    ("Pizzero", "pizzero", "pizzero123", "pizzero"),
]

# (nombre, categoria, unidad, stock, stock_minimo, costo_unitario)
# Varios ingredientes empiezan por debajo del minimo para que las alertas se
# vean apenas se abre la aplicacion.
INGREDIENTES_INICIALES = [
    ("Harina de trigo", "Granos", "kg", 25, 10, 4500),
    ("Levadura", "Condimentos", "kg", 0.9, 0.4, 20000),
    ("Salsa de tomate", "Salsas", "L", 12, 5, 9800),
    ("Queso mozzarella", "Lácteos", "kg", 6, 8, 28000),        # alerta: stock bajo
    ("Queso parmesano", "Lácteos", "kg", 2, 1, 45000),
    ("Queso cheddar", "Lácteos", "kg", 2.5, 1, 32000),
    ("Queso azul", "Lácteos", "kg", 0, 0.5, 52000),            # alerta: agotado
    ("Pepperoni", "Carnes", "kg", 4, 3, 34000),
    ("Jamón", "Carnes", "kg", 2.5, 3, 26000),                  # alerta: stock bajo
    ("Carne molida", "Carnes", "kg", 4, 2, 24000),
    ("Piña en almíbar", "Frutas", "kg", 5, 2, 12000),
    ("Champiñones", "Verduras", "kg", 1.5, 2, 15000),          # alerta: stock bajo
    ("Pimentón", "Verduras", "kg", 3, 1.5, 8000),
    ("Cebolla", "Verduras", "kg", 6, 3, 5000),
    ("Aceitunas negras", "Verduras", "kg", 0.8, 1, 22000),     # alerta: stock bajo
    ("Jalapeños", "Verduras", "kg", 1.2, 0.5, 18000),
    ("Aceite de oliva", "Aceites", "L", 3, 2, 32000),
    ("Orégano", "Condimentos", "kg", 0.6, 0.3, 40000),
]

# Menu: nombre, descripcion, precio de la pizza mediana y receta
# {ingrediente: cantidad para una pizza mediana}.
PIZZAS_INICIALES = [
    (
        "Margarita",
        "La clásica: salsa de tomate, mozzarella y orégano.",
        28000,
        {"Harina de trigo": 0.30, "Levadura": 0.01, "Salsa de tomate": 0.15,
         "Queso mozzarella": 0.25, "Orégano": 0.005, "Aceite de oliva": 0.02},
    ),
    (
        "Pepperoni",
        "Mozzarella y generosas rodajas de pepperoni.",
        34000,
        {"Harina de trigo": 0.30, "Levadura": 0.01, "Salsa de tomate": 0.15,
         "Queso mozzarella": 0.25, "Pepperoni": 0.12, "Orégano": 0.005},
    ),
    (
        "Hawaiana",
        "Jamón y piña sobre base de mozzarella.",
        33000,
        {"Harina de trigo": 0.30, "Levadura": 0.01, "Salsa de tomate": 0.15,
         "Queso mozzarella": 0.25, "Jamón": 0.10, "Piña en almíbar": 0.12},
    ),
    (
        "Cuatro Quesos",
        "Mozzarella, parmesano, cheddar y queso azul.",
        38000,
        {"Harina de trigo": 0.30, "Levadura": 0.01, "Salsa de tomate": 0.10,
         "Queso mozzarella": 0.20, "Queso parmesano": 0.06, "Queso cheddar": 0.07,
         "Queso azul": 0.05},
    ),
    (
        "Vegetariana",
        "Champiñones, pimentón, cebolla y aceitunas negras.",
        31000,
        {"Harina de trigo": 0.30, "Levadura": 0.01, "Salsa de tomate": 0.15,
         "Queso mozzarella": 0.20, "Champiñones": 0.08, "Pimentón": 0.06,
         "Cebolla": 0.06, "Aceitunas negras": 0.04},
    ),
    (
        "Mexicana",
        "Carne molida, jalapeños y cebolla. Picante.",
        36000,
        {"Harina de trigo": 0.30, "Levadura": 0.01, "Salsa de tomate": 0.15,
         "Queso mozzarella": 0.22, "Carne molida": 0.12, "Jalapeños": 0.04,
         "Cebolla": 0.05},
    ),
]


def sembrar_datos(conexion: sqlite3.Connection) -> None:
    """Carga usuarios, ingredientes, menu y dos pedidos de ejemplo."""
    # --- Usuarios ---
    conexion.executemany(
        "INSERT INTO usuario (nombre, usuario, clave_hash, rol) VALUES (?, ?, ?, ?)",
        [(nombre, usuario, cifrar_clave(clave), rol)
         for nombre, usuario, clave, rol in USUARIOS_INICIALES],
    )

    # --- Ingredientes ---
    conexion.executemany(
        """INSERT INTO ingrediente (nombre, categoria, unidad, stock, stock_minimo, costo_unitario)
           VALUES (?, ?, ?, ?, ?, ?)""",
        INGREDIENTES_INICIALES,
    )

    # Diccionario {nombre del ingrediente: id} para armar las recetas.
    ids_ingredientes = {
        fila["nombre"]: fila["id"]
        for fila in conexion.execute("SELECT id, nombre FROM ingrediente")
    }

    # --- Pizzas y sus recetas ---
    for nombre, descripcion, precio, receta in PIZZAS_INICIALES:
        cursor = conexion.execute(
            "INSERT INTO pizza (nombre, descripcion, precio_base, activa) VALUES (?, ?, ?, 1)",
            (nombre, descripcion, precio),
        )
        pizza_id = cursor.lastrowid
        conexion.executemany(
            "INSERT INTO receta (pizza_id, ingrediente_id, cantidad) VALUES (?, ?, ?)",
            [(pizza_id, ids_ingredientes[ingrediente], cantidad)
             for ingrediente, cantidad in receta.items()],
        )
    conexion.commit()

    # --- Pedidos de ejemplo ---
    # Se crean con el mismo servicio que usa la aplicacion para que el descuento
    # de inventario quede exactamente igual que en un pedido real.
    # La importacion va aqui dentro para no crear una dependencia circular.
    from app.servicios import pedidos as servicio_pedidos

    id_cajero = conexion.execute(
        "SELECT id FROM usuario WHERE usuario = 'cajero'").fetchone()["id"]
    ids_pizzas = {
        fila["nombre"]: fila["id"]
        for fila in conexion.execute("SELECT id, nombre FROM pizza")
    }

    servicio_pedidos.crear_pedido(
        conexion,
        modalidad="mesa",
        cliente="Familia Ramírez",
        referencia="Mesa 5",
        notas="Sin orégano en una de las pizzas.",
        usuario_id=id_cajero,
        lineas=[
            {"pizza_id": ids_pizzas["Margarita"], "tamano": "familiar", "cantidad": 1},
            {"pizza_id": ids_pizzas["Pepperoni"], "tamano": "mediana", "cantidad": 1},
        ],
    )
    servicio_pedidos.crear_pedido(
        conexion,
        modalidad="domicilio",
        cliente="Carlos Pérez",
        referencia="Calle 45 # 12-30, Apto 302",
        notas="Timbre dañado, llamar al llegar.",
        usuario_id=id_cajero,
        lineas=[
            {"pizza_id": ids_pizzas["Hawaiana"], "tamano": "mediana", "cantidad": 2},
        ],
    )
