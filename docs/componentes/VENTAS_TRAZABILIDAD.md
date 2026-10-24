# Ventas y trazabilidad

## Propósito

Esta parte de FarmaStock se encarga de registrar las ventas y mantener el control de los cambios que estas producen en el inventario.

La idea es que cada venta actualice las existencias de forma automática y que los movimientos importantes queden registrados para poder revisarlos después.

## Registro de ventas

El archivo `app/services/sale_service.py` contiene la lógica utilizada para registrar las ventas.

Antes de confirmar una operación, el sistema verifica que exista suficiente producto disponible. Cuando la venta se registra correctamente, las cantidades vendidas se descuentan del inventario.

Si un producto tiene existencias con diferentes fechas de vencimiento, el sistema utiliza primero las que vencen antes, siguiendo el criterio FEFO.

## Anulación de ventas

Una venta registrada incorrectamente no se elimina directamente.

El sistema permite anularla indicando el motivo. Al realizar la anulación, las cantidades relacionadas con esa venta se devuelven al inventario para mantener las existencias correctas.

La venta queda registrada como anulada para conservar el historial de lo ocurrido.

## Trazabilidad de movimientos

El archivo `app/services/audit_service.py` se utiliza para guardar información sobre acciones importantes realizadas dentro del sistema.

Esto permite mantener un registro de operaciones como anulaciones y otros cambios que necesitan quedar identificados.

La finalidad es evitar que modificaciones importantes ocurran sin dejar evidencia dentro del sistema.

## Resumen del dashboard

El archivo `app/services/dashboard_service.py` obtiene información utilizada en el panel principal de FarmaStock.

Desde este servicio se preparan datos que permiten mostrar un resumen del estado actual del negocio, como información relacionada con ventas, inventario y alertas disponibles.

El dashboard funciona como una consulta rápida y no modifica directamente las existencias.

## Archivos principales

- `app/services/sale_service.py`: registro y anulación de ventas.
- `app/services/audit_service.py`: registro de acciones importantes realizadas en el sistema.
- `app/services/dashboard_service.py`: información utilizada para mostrar el resumen del panel principal.

## Relación con otros módulos

Las ventas están directamente relacionadas con el inventario, ya que cada operación confirmada reduce las existencias disponibles.

Cuando una venta se anula, el sistema devuelve las cantidades correspondientes. La información generada por estos movimientos también puede ser utilizada posteriormente por los reportes y el dashboard.
