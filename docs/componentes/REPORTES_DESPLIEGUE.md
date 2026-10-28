# FarmaStock — Reportes y Despliegue

## 1. Descripción

Esta rama está destinada al desarrollo y la documentación de funcionalidades relacionadas con la generación de reportes y la preparación del sistema FarmaStock para su despliegue.

## 2. Objetivos

- Documentar la generación y exportación de reportes.
- Facilitar la consulta de información relacionada con los vencimientos de productos.
- Verificar el funcionamiento mediante pruebas automatizadas.
- Preparar la documentación técnica necesaria para ejecutar y mantener el sistema.

## 3. Reportes de vencimientos

El sistema contempla la generación de reportes de vencimientos con exportación a formato Excel (`.xlsx`).

El archivo de reporte incluye las siguientes hojas:

- **Próximos a vencer:** información sobre productos cuyos vencimientos requieren seguimiento.
- **Vencidos:** información sobre productos que ya superaron su fecha de vencimiento.

La generación del reporte se realiza mediante el servicio `ReportService`, utilizando el método `export_expirations()`.

## 4. Validaciones y pruebas

Se dispone de pruebas automatizadas para verificar diferentes reglas de negocio y operaciones del sistema.

Entre las validaciones relacionadas con inventario y reportes se encuentran:

- Generación correcta del archivo Excel de vencimientos.
- Existencia de las hojas correspondientes en el archivo exportado.
- Separación entre existencias totales, vendibles, bloqueadas y vencidas.
- Prevención de ventas de productos vencidos.
- Aplicación de las reglas de control de vencimientos.

También existen pruebas para ventas, entradas de inventario, ajustes, usuarios, respaldos y configuración.

## 5. Tecnologías y herramientas

- Python.
- SQLite para la persistencia de datos.
- Git y GitHub para el control de versiones.
- `unittest` para las pruebas automatizadas.
- `openpyxl` para la lectura y validación de archivos Excel en las pruebas.

## 6. Ejecución de pruebas

Desde la raíz del proyecto, se pueden ejecutar las pruebas con el comando correspondiente a la estructura del repositorio.

Por ejemplo, si las pruebas están organizadas en el directorio `tests`:

```bash
python -m unittest discover -s tests -v
```

Se debe verificar que las pruebas finalicen correctamente antes de integrar los cambios.

## 7. Flujo de trabajo con Git

La rama de trabajo es:

```text
feat/reportes-despliegue
```

Para publicar los cambios en GitHub:

```bash
git add .
git commit -m "feat: documentar reportes y despliegue"
git push -u origin feat/reportes-despliegue
```

Una vez publicados los cambios, se puede crear un Pull Request hacia la rama de integración definida por el equipo.

## 8. Pendientes de despliegue

Antes de considerar terminado el despliegue, se recomienda documentar y verificar:

- Requisitos de instalación y ejecución.
- Configuración de la base de datos.
- Dependencias necesarias.
- Ubicación y permisos de los respaldos.
- Procedimiento de instalación en el entorno destino.
- Verificación del funcionamiento después del despliegue.

## 9. Estado

La documentación y las pruebas deben actualizarse conforme se incorporen nuevas funcionalidades a la rama.
