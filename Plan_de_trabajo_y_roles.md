# Plan de trabajo y roles - FarmaStock

## Cómo vamos a trabajar

Como equipo decidimos dividir el desarrollo de **FarmaStock** por partes para que cada integrante tenga una responsabilidad clara. La idea es trabajar de forma ordenada, evitar que varias personas modifiquen lo mismo al mismo tiempo y poder revisar cada aporte antes de integrarlo al proyecto.

El repositorio tendrá una rama `main`, que se mantendrá como la versión estable, y una rama `develop`, donde iremos uniendo el trabajo de cada integrante. Cada parte se trabajará en una rama separada y se integrará mediante Pull Request.

## Integrantes y responsabilidades

| Integrante | Área asignada | Responsabilidad |
|---|---|---|
| Heredia Ramos Ricardo Enrique | Base del sistema y persistencia | Preparar la base de ejecución, configuración, SQLite y seguridad local. Al final elaborará el manual de usuario. |
| Barrera Magaña Douglas Isaac | Productos e inventario | Integrar productos, entradas de mercadería, existencias, lotes y conteos físicos. |
| Calderón Calderón Gabriel Omar | Ventas y trazabilidad | Integrar ventas, anulaciones, auditoría de movimientos y datos del panel principal. |
| Siguenza Quele Douglas Enrique | Usuarios y respaldos | Integrar usuarios, configuraciones, respaldos y restauración de la información. |
| Alvarenga Alvarenga Alexis Alfonso | Interfaz | Integrar las pantallas, componentes visuales e identidad gráfica de FarmaStock. |
| Angel Guevara José Franklin | Reportes, pruebas y despliegue | Integrar reportes, pruebas automatizadas, ejecutable e instalador. |

## Ramas que utilizaremos

- `main`: versión estable del proyecto.
- `develop`: rama donde se integrará el trabajo del equipo.
- `feat/core-persistencia`
- `feat/productos-inventario`
- `feat/ventas-trazabilidad`
- `feat/usuarios-respaldos`
- `feat/interfaz-farmastock`
- `feat/reportes-despliegue`
- `docs/manual-usuario`

## Cronograma del equipo

| Fecha | Actividad | Responsable | Evidencia |
|---|---|---|---|
| 20/10/2026 | Crear el repositorio y agregar el README inicial | Ricardo | Commit inicial |
| 21/10/2026 | Crear `develop` e integrar la base, configuración y persistencia | Ricardo | Rama, commits y Pull Request |
| 21-22/10/2026 | Integrar productos, entradas e inventario | Douglas Barrera | Commits, Pull Request y pruebas |
| 22-23/10/2026 | Integrar ventas y trazabilidad | Gabriel | Commits, Pull Request y pruebas |
| 23-24/10/2026 | Integrar usuarios, configuraciones y respaldos | Douglas Siguenza | Commits, Pull Request y pruebas |
| 24-25/10/2026 | Integrar interfaz e identidad visual | Alexis | Commits, Pull Request y revisión visual |
| 25-26/10/2026 | Integrar reportes, pruebas y archivos de instalación | José Franklin | Commits, Pull Request y resultados de pruebas |
| 27-28/10/2026 | Revisar en conjunto la versión integrada en `develop` | Equipo | Revisiones y pruebas generales |
| 29-30/10/2026 | Probar FarmaStock con el negocio y recopilar observaciones | Equipo | Evidencias y comentarios recibidos |
| 30/10-01/11/2026 | Elaborar el manual de usuario con capturas y pasos | Ricardo | Manual de usuario |
| 01-02/11/2026 | Revisar la entrega y practicar la exposición | Equipo | Revisión final y ensayo |
| 03/11/2026 | Entrega final | Equipo | Proyecto completo |

## Cómo revisaremos los cambios

Cada integrante trabajará solamente en la parte que tiene asignada. Cuando termine, abrirá un Pull Request hacia `develop` y otro compañero revisará los cambios antes de integrarlos.

Si durante una revisión se encuentra algo que debe corregirse, el mismo integrante realizará el ajuste en su rama. Con esto buscamos que el historial del repositorio muestre de forma clara quién trabajó cada parte.

## Evidencias que vamos a guardar

Durante el proceso guardaremos las ramas utilizadas, los commits de cada integrante, los Pull Requests, las revisiones realizadas y los resultados de las pruebas.

También tomaremos capturas del repositorio donde se pueda ver el historial de trabajo y los contribuidores. Estas evidencias se utilizarán para mostrar cómo se repartieron las tareas y cómo se fue integrando el proyecto.

## Manual de usuario

El manual se realizará cuando la versión de FarmaStock ya esté cerrada. Esto permitirá utilizar capturas reales y evitar repetir el trabajo si alguna pantalla cambia durante la integración.

El manual explicará la instalación, acceso al sistema, productos, entradas, ventas, inventario, alertas, reportes, respaldos y cierre de sesión. La redacción será sencilla para que pueda utilizarlo una persona sin conocimientos técnicos.

## Preparación para la exposición

Aunque cada integrante tendrá un área principal, todos debemos conocer el problema identificado, la solución que se desarrolló y el funcionamiento general de FarmaStock.

Antes de la entrega haremos un ensayo para que cualquiera de los seis pueda explicar el proyecto y realizar un recorrido básico por el sistema.

## Cierre del trabajo

Daremos por terminada la integración cuando todos los aportes estén unidos en `develop`, las pruebas se ejecuten correctamente, se haya realizado la prueba con el negocio y el manual esté terminado.

Después de esa revisión se integrará `develop` a `main` como versión final del proyecto.