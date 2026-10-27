# Usuarios, configuración y respaldos

## Propósito

Esta parte de FarmaStock se encarga del acceso de los usuarios, la administración de roles, la configuración general relacionada con el funcionamiento del sistema y la creación y restauración de respaldos.

El objetivo es mantener control sobre quién puede ingresar al sistema y proteger la información local mediante copias de seguridad que puedan utilizarse en caso de ser necesario.

## Usuarios y acceso

El archivo `app/services/auth_service.py` contiene las funciones relacionadas con el acceso y administración de usuarios.

Cada usuario cuenta con un nombre, un nombre de usuario, una contraseña, un rol y un estado que permite indicar si se encuentra activo.

Actualmente se manejan los roles:

- `ADMIN`
- `OPERADOR`

El sistema verifica el usuario y la contraseña antes de permitir el acceso.

Las contraseñas no se guardan directamente. Para validarlas se utilizan las funciones de seguridad definidas en el proyecto.

## Administrador inicial

Cuando el sistema no tiene usuarios registrados, se crea un usuario administrador inicial.

Este usuario permite realizar el primer acceso y comenzar la configuración de FarmaStock.

El sistema también procura que el usuario `admin` conserve el rol de administrador.

## Administración de usuarios

Desde el servicio de autenticación se pueden realizar operaciones como:

- crear usuarios;
- consultar usuarios registrados;
- modificar nombre, usuario y rol;
- cambiar contraseñas;
- activar o desactivar usuarios.

El nombre de usuario debe ser único para evitar que existan dos cuentas con el mismo identificador.

Las contraseñas deben tener al menos 6 caracteres.

## Protección del último administrador

FarmaStock evita que el sistema quede sin un administrador activo.

Si solamente existe un administrador activo, no se permite quitarle el rol de administrador ni desactivar su cuenta.

Esta validación ayuda a evitar que el sistema quede sin una cuenta con permisos para administrar usuarios y configuraciones.

## Configuración

El archivo `app/services/settings_service.py` se utiliza para manejar las preferencias y valores configurables de FarmaStock.

Dentro de este bloque también se encuentra la política relacionada con fechas de vencimiento.

La configuración se mantiene separada de otras partes del sistema para evitar colocar valores directamente dentro de los módulos de inventario, ventas o interfaz.

## Manejo de fechas

El archivo `app/date_utils.py` contiene funciones utilizadas para mostrar fechas y horas de una forma consistente dentro de FarmaStock.

Las fechas se muestran normalmente con el formato:

`dd/mm/aaaa`

Las fechas que incluyen hora se muestran como:

`dd/mm/aaaa hh:mm`

También se incluye una función para mostrar tamaños de archivos en unidades como:

- B
- KB
- MB
- GB

Esta función puede utilizarse, por ejemplo, para mostrar de una forma más clara el tamaño de los archivos de respaldo.

## Respaldos

El archivo `app/services/backup_service.py` se encarga de crear y restaurar copias de la base de datos de FarmaStock.

Los respaldos se almacenan como archivos de base de datos SQLite.

El sistema permite trabajar con respaldos manuales y automáticos.

## Respaldo manual

Se puede crear una copia manual de la base de datos cuando sea necesario.

Si no se indica una ubicación específica, el archivo se guarda dentro de la carpeta destinada a respaldos.

El nombre del archivo incluye la fecha y hora para facilitar su identificación.

Un ejemplo sería:

`inventario_backup_20261024_153000.db`

## Respaldos automáticos

FarmaStock maneja dos tipos principales de respaldo automático.

Al iniciar el sistema puede crearse un archivo con el formato:

`backup_inicio_YYYYMMDD.db`

Este respaldo representa el estado de la información al inicio del día.

También se mantiene:

`backup_ultimo_cierre.db`

Este archivo representa la copia más reciente creada al cerrar normalmente la aplicación.

El respaldo de último cierre se reemplaza para evitar crear un archivo diferente cada vez que se abre y cierra FarmaStock.

## Conservación de respaldos

Los respaldos automáticos de inicio se conservan por un período limitado.

Actualmente el sistema mantiene los respaldos correspondientes a los últimos 7 días.

Los respaldos más antiguos pueden eliminarse automáticamente para evitar acumular archivos sin límite.

Los respaldos manuales no forman parte de esta eliminación automática.

## Validación de respaldos

Antes de restaurar un archivo, FarmaStock verifica que sea una base SQLite válida.

También comprueba que contenga las tablas y columnas principales esperadas por el sistema.

Entre las tablas verificadas se encuentran:

- usuarios;
- productos;
- entradas;
- lotes;
- ventas;
- detalle de ventas;
- movimientos de inventario.

Si el archivo no corresponde a una base válida de FarmaStock, la restauración no continúa.

## Restauración

Cuando se solicita restaurar un respaldo, el sistema primero crea una copia de seguridad del estado actual.

Esta copia utiliza un nombre similar a:

`antes_de_restaurar_YYYYMMDD_HHMMSS.db`

Después se carga la información del respaldo seleccionado.

De esta forma se conserva una copia previa de la base antes de reemplazar la información.

## Historial de respaldos

FarmaStock registra información sobre los respaldos realizados.

El historial permite conservar datos como:

- nombre del archivo;
- ubicación;
- tamaño;
- fecha y hora;
- tipo de respaldo.

Entre los tipos de respaldo pueden encontrarse copias manuales, automáticas, previas a una restauración y archivos utilizados para restaurar.

## Revisión de la base de datos

El servicio de respaldos también puede comprobar el estado básico de la base de datos.

Se verifica su integridad, la existencia de las tablas principales y posibles problemas relacionados con referencias entre registros.

Si se detecta un problema, el servicio devuelve la información encontrada para que pueda revisarse.

## Archivos principales

- `app/services/auth_service.py`: acceso, usuarios, roles y protección del último administrador.
- `app/services/settings_service.py`: preferencias y configuración del sistema.
- `app/services/backup_service.py`: creación, control y restauración de respaldos.
- `app/date_utils.py`: manejo y presentación de fechas, horas y tamaños de archivo.

## Relación con otros módulos

El bloque de usuarios permite controlar quién puede ingresar a FarmaStock y qué tipo de acceso posee.

La configuración proporciona valores que pueden ser utilizados por otras funciones del sistema, como el control relacionado con vencimientos.

Los respaldos trabajan directamente con la base de datos local y permiten conservar copias de la información de productos, inventario, ventas y usuarios.

Este bloque no modifica directamente las reglas de inventario, ventas, interfaz o reportes.