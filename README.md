# 💊 FarmaStock

**Sistema de gestión de inventario y ventas para un pequeño negocio de medicamentos de venta libre y productos de cuidado personal.**

FarmaStock es una aplicación de escritorio que facilita el registro de productos, entradas de mercadería, ventas y existencias. Centraliza la información del negocio y funciona localmente en Windows, sin depender de una conexión permanente a Internet.

## ✨ Funcionalidades principales

- **Productos:** registro, edición, búsqueda y consulta.
- **Inventario:** control de existencias, lotes, vencimientos y ajustes por conteo físico.
- **Entradas:** registro de nueva mercadería y actualización de existencias.
- **Ventas:** registro de operaciones, descuento automático de existencias y anulación de ventas.
- **Alertas:** productos con existencias bajas, próximos a vencer y vencidos.
- **Reportes:** consultas y exportación a PDF y Excel.
- **Respaldos:** creación y restauración de copias de seguridad.
- **Usuarios:** administración de cuentas y permisos de acceso.

## 🛠️ Tecnologías utilizadas

| Tecnología | Utilización |
|---|---|
| Python | Desarrollo de la aplicación |
| CustomTkinter | Interfaz gráfica |
| SQLite | Almacenamiento local |
| PyInstaller | Generación del ejecutable |
| Inno Setup | Creación del instalador para Windows |

## 💻 Instalación

1. Acceda a la sección [Releases](https://github.com/Doisaac/FarmaStock/releases).
2. Descargue el instalador de FarmaStock para Windows.
3. Ejecute el archivo descargado y siga las instrucciones del instalador.
4. Abra FarmaStock desde el acceso directo creado.
5. Inicie sesión con las credenciales asignadas.

La aplicación funciona de forma local y **no requiere instalar Python ni configurar un servidor de base de datos**.

## 📖 Manual de usuario

El manual explica, con pasos y capturas de pantalla, cómo utilizar las principales funciones del sistema.

**[Consultar el Manual de Usuario de FarmaStock](docs/Manual_de_Usuario_FarmaStock.pdf)**

## 📅 Cronograma del proyecto

El siguiente cronograma recoge la planificación del equipo y las evidencias previstas para cada actividad.

| Fecha | Actividad | Responsable | Evidencia prevista |
|---|---|---|---|
| 20/10/2026 | Crear el repositorio y agregar el README inicial | Ricardo | Commit inicial |
| 21/10/2026 | Crear `develop` e integrar base, configuración y persistencia | Ricardo | Rama, commits y Pull Request |
| 21–22/10/2026 | Integrar productos, entradas e inventario | Douglas Barrera | Commits, Pull Request y pruebas |
| 22–23/10/2026 | Integrar ventas y trazabilidad | Gabriel | Commits, Pull Request y pruebas |
| 23–24/10/2026 | Integrar usuarios, configuración y respaldos | Douglas Siguenza | Commits, Pull Request y pruebas |
| 24–27/10/2026 | Integrar interfaz e identidad visual | Alexis | Commits, Pull Request y revisión visual |
| 27/10/2026 | Integrar reportes, pruebas y archivos de instalación | José Franklin | Commits, Pull Request y resultados de pruebas |
| 28/10/2026 | Revisar en conjunto la versión integrada en `develop` | Equipo | Revisiones y pruebas generales |
| 29/10/2026 | Elaborar el manual de usuario con capturas y pasos | Ricardo | Manual de usuario |
| 30–31/10/2026 | Probar FarmaStock con el negocio y recopilar observaciones | Ricardo | Evidencias y comentarios recibidos |
| 01/11/2026 | Revisar la entrega y practicar la exposición | Equipo | Revisión final y ensayo |
| 03/11/2026 | Entrega final | Equipo | Proyecto completo |

## 👥 Equipo de desarrollo

| Integrante | Responsabilidad principal |
|---|---|
| Ricardo Enrique Heredia Ramos | Base del sistema, persistencia, manual de usuario y validación |
| Douglas Isaac Barrera Magaña | Productos e inventario |
| Gabriel Omar Calderón Calderón | Ventas y trazabilidad |
| Douglas Enrique Siguenza Quele | Usuarios, configuración y respaldos |
| Alexis Alfonso Alvarenga Alvarenga | Interfaz e identidad visual |
| José Franklin Angel Guevara | Reportes, pruebas y despliegue |

## 🧩 Organización del desarrollo

El equipo trabaja por módulos y utiliza **ramas y Pull Requests** para revisar e integrar cambios. La rama `develop` reúne el trabajo del equipo y `main` se reserva para la versión estable.

---

**Proyecto académico · Asesoría Profesional (APR135) · Ingeniería en Desarrollo de Software · Universidad de El Salvador · 2026**