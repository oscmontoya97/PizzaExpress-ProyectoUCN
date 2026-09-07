# Pizza Express — Sistema de Gestión de Pedidos e Inventario

Aplicación web desarrollada en **Python** para la pizzería *Pizza Express*. Digitaliza la toma
de pedidos y el control del inventario en tiempo real, con el objetivo de **reducir errores en
los pedidos** y **evitar quiebres de ingredientes durante el servicio**.

Proyecto de la asignatura de Ingeniería de Software — Católica del Norte Fundación Universitaria.

---

## 1. Requerimientos que cumple

Los requerimientos se tomaron de la presentación del proyecto (`PizzaExpress_Presentacion.pptx`),
alcance de la versión 1:

| ID | Requerimiento | Dónde está implementado |
|----|---------------|-------------------------|
| RF1 | Pedidos en tres modalidades: **mesa, para llevar y domicilio** | `app/servicios/pedidos.py`, `app/vistas/pedidos.py` |
| RF2 | **Inventario con descuento automático por pizza** (según su receta) | `app/servicios/inventario.py` → `calcular_consumo` y `descontar_receta` |
| RF3 | **Alertas de stock mínimo** | `app/servicios/inventario.py` → `obtener_alertas`; pantalla `/inventario/alertas` |
| RF4 | **Reportes básicos de ventas** | `app/servicios/reportes.py`, pantalla `/reportes` |
| RF5 | Inventario en tiempo real y **bloqueo de la venta si falta un insumo clave** | `app/servicios/inventario.py` → `verificar_disponibilidad` |
| RF6 | Gestión de inventario, precios y reabastecimiento (administrador) | `app/vistas/inventario.py`, `app/vistas/menu.py` |
| RF7 | Seguimiento del pedido por parte de la cocina | `app/vistas/cocina.py` (tablero por estados) |

**Fuera de alcance en esta versión** (así se definió en la presentación): pagos en línea,
aplicación de repartidores con GPS y programa de fidelización.

**Actores del sistema** (roles con los que se puede iniciar sesión):

| Rol | Qué puede hacer |
|-----|-----------------|
| Administrador / dueño | Todo: pedidos, cocina, inventario, precios del menú y reportes |
| Cajero / mesero | Registrar y consultar pedidos, ver el menú, el inventario y las alertas |
| Pizzero / cocina | Tablero de la cocina (avanzar el estado de los pedidos), menú y alertas |

---

## 2. Documentación del proyecto

La carpeta [`docs/`](docs/) contiene la documentación completa de la entrega, en Markdown y en
PDF:

| Documento | Contenido |
|---|---|
| [Plan de pruebas del sistema](docs/plan-de-pruebas.md) · [PDF](docs/plan-de-pruebas.pdf) | Estrategia, casos de prueba con sus resultados, matriz de trazabilidad y defectos encontrados |
| [Documentación técnica](docs/documentacion-tecnica.md) · [PDF](docs/documentacion-tecnica.pdf) | Arquitectura, modelo de datos, algoritmos, rutas, seguridad y guía de mantenimiento |
| [Manual de usuario](docs/manual-de-usuario.md) · [PDF](docs/manual-de-usuario.pdf) | Cómo usar el sistema, paso a paso y con capturas, para cada rol |
| [Estrategia de gestión del proyecto](docs/gestion-del-proyecto.md) · [PDF](docs/gestion-del-proyecto.pdf) | Alcance, metodología Scrum, cronograma, riesgos, herramientas y entregables |

Los PDF se regeneran con `python3 docs/generar_pdf.py` (necesita el módulo `markdown` y Chrome).

---

## 3. Requisitos previos

- **Python 3.10 o superior** (se probó con Python 3.13).
- No hace falta instalar ningún motor de base de datos: se usa **SQLite**, incluido en Python.

---

## 4. Instalación

```bash
# 1. Entrar a la carpeta del proyecto
cd Ing-Soft-Pizzeria-Python

# 2. Crear un entorno virtual (recomendado)
python3 -m venv .venv

# 3. Activar el entorno virtual
source .venv/bin/activate        # macOS o Linux
.venv\Scripts\activate           # Windows

# 4. Instalar la única dependencia (Flask)
pip install -r requirements.txt
```

---

## 5. Ejecución

```bash
python ejecutar.py
```

Luego abrir en el navegador: **http://127.0.0.1:5000**

La primera vez la aplicación crea sola la base de datos `datos/pizzaexpress.db` y la llena con
datos de ejemplo (18 ingredientes, 6 pizzas con su receta, 3 usuarios y 2 pedidos).

### Usuarios de prueba

| Usuario | Contraseña | Rol |
|---------|-----------|-----|
| `admin` | `admin123` | Administrador / dueño |
| `cajero` | `cajero123` | Cajero / mesero |
| `pizzero` | `pizzero123` | Pizzero / cocina |

### Reiniciar los datos

Basta con borrar la base de datos; se vuelve a crear al ejecutar la aplicación:

```bash
rm datos/pizzaexpress.db
```

---

## 6. Cómo probar la aplicación de punta a punta

1. Entrar como **cajero** → *Pedidos* → *Nuevo pedido*. Elegir la modalidad (mesa, para llevar o
   domicilio), escribir el cliente y poner cantidades a una o varias pizzas. Al guardar, el
   inventario se descuenta automáticamente.
2. Intentar pedir una **Cuatro Quesos**: la venta se **bloquea** porque el queso azul empieza
   agotado, y el sistema dice exactamente qué insumo falta y cuánto.
3. Entrar como **administrador** → *Alertas* → reabastecer el queso azul. Ahora la Cuatro Quesos
   sí se puede vender.
4. Entrar como **pizzero** → *Cocina* → avanzar el pedido: pendiente → en preparación → lista →
   entregado. Si se cancela un pedido, los ingredientes vuelven al inventario.
5. Entrar como **administrador** → *Reportes* para ver las ventas del periodo, las pizzas más
   vendidas y el desglose por modalidad y por tamaño.

### Pruebas automáticas

```bash
python -m unittest discover -s pruebas -v
```

Son 18 pruebas sobre la lógica de negocio (descuento por receta, bloqueo de venta, ciclo de
estados, devolución de stock al cancelar, reportes y autenticación). Usan una base de datos en
memoria, así que **no modifican los datos de la aplicación**.

---

## 7. Estructura del proyecto

```
Ing-Soft-Pizzeria-Python/
├── ejecutar.py                 # Punto de entrada: crea la BD y levanta el servidor
├── requirements.txt            # Única dependencia: Flask
├── assets/                     # Archivos estáticos (se sirven en /assets)
│   ├── logo.png                # Logo de Pizza Express extraído de la presentación
│   └── estilos.css             # Hoja de estilos propia, sin frameworks
├── datos/
│   └── pizzaexpress.db         # Base de datos SQLite (se genera automáticamente)
├── pruebas/
│   └── test_servicios.py       # Pruebas automáticas de la lógica de negocio
└── app/
    ├── __init__.py             # crear_app(): construye la aplicación Flask
    ├── configuracion.py        # Constantes: marca, tamaños, estados, modalidades, roles
    ├── basedatos.py            # Conexión SQLite, esquema y datos de ejemplo
    ├── utilidades.py           # Formato de moneda/fecha y control de acceso por rol
    ├── modelos/                # Estructuras de datos (Ingrediente, Pizza, Pedido, Usuario)
    ├── servicios/              # Lógica de negocio (no depende de Flask)
    │   ├── inventario.py       # Consumo por receta, alertas, descuento y reabastecimiento
    │   ├── menu.py             # Catálogo de pizzas, recetas, precios y disponibilidad
    │   ├── pedidos.py          # Creación de pedidos y ciclo de estados
    │   ├── reportes.py         # Reportes de ventas
    │   └── autenticacion.py    # Validación de credenciales
    ├── vistas/                 # Un blueprint de Flask por sección de la aplicación
    └── plantillas/             # Plantillas HTML (Jinja2)
```

La aplicación está organizada en **tres capas**, para que cada archivo tenga una sola
responsabilidad:

1. **Modelos** — representan los datos (una pizza, un pedido, un ingrediente).
2. **Servicios** — contienen las reglas del negocio y no saben nada de la web; por eso se
   pueden probar sin levantar el servidor.
3. **Vistas y plantillas** — reciben los datos del formulario, llaman al servicio y muestran
   el resultado en pantalla.

---

## 8. Modelo de datos

| Tabla | Para qué sirve |
|-------|----------------|
| `usuario` | Empleados del sistema y su rol. La contraseña se guarda cifrada con SHA-256 |
| `ingrediente` | Insumos: stock actual, **stock mínimo** (umbral de alerta), unidad y costo |
| `pizza` | Menú: nombre, descripción y precio base (tamaño mediano) |
| `receta` | **Qué ingredientes y cuánto consume cada pizza.** Es la tabla que permite descontar el inventario automáticamente |
| `pedido` | Cabecera: código, modalidad, cliente, estado, total y quién lo tomó |
| `detalle_pedido` | Líneas del pedido: pizza, tamaño, cantidad y precio en el momento de la venta |

### Reglas de negocio principales

- **Tamaños**: personal (×0,6), mediana (×1,0) y familiar (×1,6). El factor multiplica a la vez
  el precio de venta y las cantidades de la receta que se descuentan del inventario.
- **Descuento automático**: al registrar un pedido se recorre la receta de cada pizza, se suman
  los ingredientes compartidos entre pizzas y se descuenta todo en una sola transacción.
- **Bloqueo de venta**: antes de descontar nada se comprueba que haya stock suficiente. Si falta
  algo, no se guarda el pedido ni se toca el inventario, y se muestra qué insumo falta.
- **Ciclo del pedido**: `pendiente → en preparación → lista → entregado`. Se puede cancelar
  mientras no esté entregado; al cancelar, los ingredientes **vuelven** al inventario.
- **Alerta de stock**: un ingrediente entra en alerta cuando `stock <= stock mínimo`; si además
  llega a cero, aparece como *agotado*.
- **Reportes**: los pedidos cancelados nunca cuentan como venta.

---

## 9. Decisiones técnicas

**Python + Flask en lugar de Django.** La presentación proponía Python con Django. Se mantuvo
el lenguaje (Python) pero se usó **Flask**, un framework web más pequeño del mismo ecosistema,
porque para un prototipo académico de este tamaño:

- deja el código a la vista (no hay configuración generada automáticamente), lo que facilita
  explicar y sustentar cada archivo;
- necesita **una sola dependencia** en lugar de una decena de paquetes;
- permite escribir el SQL directamente y así mostrar el modelo de datos, en vez de esconderlo
  detrás de un ORM.

**SQLite con el módulo `sqlite3` de la biblioteca estándar**, para no depender de un servidor de
base de datos y poder entregar el proyecto en una carpeta que funciona tal cual.

**Sin JavaScript ni librerías externas de interfaz**: la aplicación funciona sin conexión a
internet y toda la validación importante se hace en el servidor, donde están las reglas de negocio.

---

## 10. Marca

El nombre **Pizza Express** y su logo aparecen en **todas las pantallas**: en el encabezado, en el
pie de página, en la pantalla de acceso y en el título de la pestaña del navegador. El archivo
`assets/logo.png` se extrajo de las imágenes incrustadas en la presentación del proyecto.
