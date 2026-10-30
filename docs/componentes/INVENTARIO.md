# Productos e inventario

## Propósito

Esta parte de FarmaStock se encarga de registrar los productos, controlar las entradas de mercadería y mantener actualizadas las existencias disponibles.

El objetivo es que el inventario cambie conforme se registran movimientos en el sistema, evitando depender únicamente de un conteo físico para conocer cuánto producto debería estar disponible.

## Productos

Cada producto se registra con la información necesaria para identificarlo y controlar sus existencias.

Entre los datos principales se encuentran el nombre, precio, unidad de control y cantidad mínima. La unidad de control permite definir si un producto se manejará, por ejemplo, por blíster o por unidad.

El archivo `app/services/product_service.py` contiene las operaciones relacionadas con el registro y mantenimiento de los productos.

## Entradas de mercadería

Cuando se recibe nueva mercadería se registra una entrada indicando el producto, la cantidad recibida y su fecha de vencimiento.

Cada entrada se conserva por separado para poder manejar productos que ingresan en diferentes momentos y que pueden tener distintas fechas de vencimiento.

El sistema genera un identificador interno para cada entrada y aumenta automáticamente las existencias del producto correspondiente.

Esta parte se maneja desde `app/services/entry_service.py`.

## Control del inventario

El archivo `app/services/inventory_service.py` se utiliza para consultar las existencias y registrar ajustes cuando se realiza un conteo físico.

El inventario toma en cuenta los movimientos registrados en el sistema. Las entradas aumentan las cantidades disponibles y las ventas las reducen.

Los conteos físicos continúan siendo necesarios para comprobar que la cantidad registrada coincida con lo que realmente existe en el negocio.

Si durante un conteo se encuentra una diferencia, se puede realizar un ajuste indicando la cantidad encontrada y el motivo de la corrección.

## Lotes y fechas de vencimiento

Un mismo producto puede tener existencias con diferentes fechas de vencimiento. Por esta razón, FarmaStock mantiene separadas las cantidades correspondientes a cada entrada.

Esto permite conocer qué existencias vencen primero y ayuda a utilizar antes los productos con una fecha de vencimiento más cercana.

Los productos vencidos o que se encuentren dentro del período configurado para bloquear su venta no se consideran como existencias disponibles para vender.

## Existencias mínimas

Cada producto puede tener una cantidad mínima configurada.

Cuando las existencias disponibles llegan o quedan por debajo de ese valor, el sistema puede identificar el producto como bajo en stock. Esta información sirve como apoyo para decidir qué productos deben revisarse antes de realizar nuevas compras.

## Archivos principales

- `app/services/product_service.py`: registro y mantenimiento de productos.
- `app/services/entry_service.py`: registro de entradas, cantidades y fechas de vencimiento.
- `app/services/inventory_service.py`: consulta de existencias, stock disponible y ajustes por conteo físico.
- `app/services/__init__.py`: archivo de inicialización de los servicios.

## Relación con otros módulos

El bloque de inventario sirve como base para otras funciones de FarmaStock.

Las ventas consultan las existencias disponibles antes de confirmar una operación y descuentan las cantidades correspondientes. Los reportes y alertas también utilizan la información del inventario para mostrar productos con pocas existencias o próximos a vencer.