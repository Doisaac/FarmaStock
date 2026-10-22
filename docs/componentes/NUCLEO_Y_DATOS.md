# Núcleo y almacenamiento local

## Propósito

Esta parte de FarmaStock contiene los archivos necesarios para iniciar la aplicación, definir la configuración general y trabajar con la base de datos local.

Se decidió utilizar SQLite porque el sistema será utilizado principalmente desde una computadora ubicada en el mostrador. De esta forma no se necesita instalar ni mantener un servidor de base de datos aparte.

## Inicio de la aplicación

El archivo `main.py` funciona como punto de entrada de FarmaStock. Desde este archivo se inicia la aplicación y se cargan los componentes necesarios para su funcionamiento.

La configuración general se encuentra en `app/config.py`. Allí se mantienen rutas y valores utilizados por distintas partes del sistema para evitar repetirlos en varios archivos.

## Base de datos

El archivo `app/database.py` se encarga de la conexión con SQLite y de preparar las tablas necesarias para almacenar la información de FarmaStock.

La base de datos permite conservar los registros de forma local en la computadora donde se utilice el sistema. Los distintos módulos de productos, inventario, ventas y usuarios utilizarán esta capa para consultar o guardar información.

La base de datos generada durante el uso no se almacena en GitHub. Cada instalación de FarmaStock tendrá sus propios datos locales.

## Seguridad local

El archivo `app/security.py` contiene funciones utilizadas para manejar información que no debe almacenarse directamente sin protección.

Estas funciones sirven como apoyo para el acceso al sistema y se mantienen separadas de la interfaz para que la lógica de seguridad pueda reutilizarse desde los servicios correspondientes.

## Archivos principales

- `main.py`: punto de entrada de FarmaStock.
- `app/__init__.py`: identifica `app` como el paquete principal de la aplicación.
- `app/config.py`: configuración y rutas utilizadas por el sistema.
- `app/database.py`: conexión y estructura de la base de datos SQLite.
- `app/security.py`: funciones de apoyo para la seguridad local.
- `requirements.txt`: dependencias necesarias para ejecutar el proyecto.

## Archivos que no se versionan

El repositorio no almacena el entorno virtual, bases de datos generadas, respaldos, ejecutables, carpetas de compilación ni reportes creados durante el uso del sistema.

Estas exclusiones se encuentran definidas en `.gitignore` para mantener el repositorio centrado en el código fuente y los archivos necesarios para trabajar con el proyecto.

