# Dzone Demo para Windows

Aplicación local de mantenimiento para supervisor y técnicos, con tickets, hallazgos, borradores revisables y reportes PDF. Incluye transcripción con **Whisper Tiny** y extracción de información con **Qwen3 4B**, ejecutadas en el equipo.

## Documentación del proyecto

- [Documentación técnica y código fuente](documentacion/Dzone%20Demo%20-%20Codigo%20fuente.docx)
- [Manual de uso ilustrado](documentacion/Dzone%20Demo%20-%20Manual%20de%20uso.docx), revisión documental 03, con flechas y acercamientos de los controles.
- [Guía para ejecutar](documentacion/Dzone%20Demo%20-%20Guia%20para%20ejecutar.docx)

Este repositorio contiene el código y los documentos. Los modelos, el motor portátil, el entorno virtual y las compilaciones no se guardan en Git. Para preparar el funcionamiento local completo, sigue los comandos de **Preparación desde código** de este README o la guía para ejecutar. La descarga inicial necesita Internet.

## Desarrolladores

- Luis Fernando Ticona Yunganina
- Juan Gedeon Tito Moya
- Smith Clever Givera Coila
- Yuri Andrea Ramos Suca
- Dimas Mijael Flores Yerba

## Requisitos
- Windows 10/11
- Python 3.11 o superior, con Tkinter (incluido normalmente en Python de python.org)
- Libreria ReportLab para generar informes PDF

## Instalar
Abre CMD en esta carpeta:

```cmd
py -m pip install -r requirements.txt
```

Inicia haciendo doble clic en `iniciar_windows.bat` o con `py dzone.py`.

Si aparece que falta ReportLab, debe instalarse en el mismo Python que abre la aplicación. El iniciador comprueba Tkinter y ReportLab antes de abrir y muestra el comando con el intérprete seleccionado si falta algo. También detecta instalaciones locales de Python que no están en PATH. Después de instalar dependencias, cierra y vuelve a abrir Dzone.

## Probar el flujo

La aplicación abre en **Iniciar sesión**. Supervisor: **demo0 / demo0**. Técnicos: **demo1 / demo1**, **demo2 / demo2**, **demo3 / demo3**, **demo4 / demo4**. No hay selector para cambiar de rol: usa **Cerrar sesión** e ingresa con otra cuenta. Si Windows no tiene un Python utilizable, `iniciar_windows.bat` también detecta el Python incluido en Codex cuando está disponible. Los errores inesperados se muestran y se registran en `%LOCALAPPDATA%\DzoneDemo\errores.log`.

1. Entra como **demo0** y crea un ticket (la base nueva está vacía). Elige **Mecanica** para probar con demo1. Pulsa **Asignar pendientes**. Se asignan los tickets cuya fecha corresponde, según prioridad, especialidad y carga. General no habilita trabajos eléctricos o mecánicos.
2. Revisa el responsable, cierra sesión e ingresa con ese técnico (usuario y contraseña iguales). Abre su ticket y pulsa **Iniciar trabajo**. Los tickets de otros técnicos no aparecen.
3. Abre el ticket de nuevo, redacta un informe tecnico (>=20 caracteres), y pulsa **Enviar reporte a validacion**.
4. Cierra sesión y vuelve con **demo0**, abre el ticket, revisa el informe y abre la evidencia. Puedes devolverlo con un motivo obligatorio o pulsar **Validar, cerrar y generar PDF**. Por defecto no se crea preventivo (0); selecciona un intervalo para autorizarlo expresamente. Si falla la generación del PDF, el ticket permanece en validación.
5. Desde **Hallazgos y aprobacion**, envia un hallazgo como tecnico; el supervisor puede aprobarlo o rechazarlo. Si aprueba, se crea un ticket nuevo.
6. En **Tablero Kanban** se visualiza el avance. En **Indicadores** se revisan conteos, mediana de tiempo de atencion y equipos con mas de un correctivo.

## Guardado de datos
La base SQLite y los PDFs se guardan en `%LOCALAPPDATA%\DzoneDemo\`. Los datos se conservan al cerrar y abrir.

## Alcance y limites
- Es una demo local en un equipo con login, sesiones y permisos verificados en las reglas de negocio. Sus credenciales son públicas de prueba; no tiene red multiusuario ni firma electrónica.
- **Asignacion automatica por reglas** (prioridad, especialidad y carga). No usa IA entrenada.
- **Prioridad sugerida por palabras clave**, requiere aprobacion del supervisor. No es IA entrenada.
- Voz: Whisper Tiny transcribe el micrófono localmente cuando sus dependencias y modelos están preparados. El formulario de hallazgos también menciona el dictado de Windows con `Win + H`, que es una función independiente del sistema operativo.
- Los reportes se pueden redactar manualmente o preparar con Qwen3 4B local. El técnico revisa y guarda el borrador antes de enviarlo; el supervisor valida el cierre y la generación del PDF.
- Calendario laboral = lunes a viernes, sin feriados regionales. Los nuevos preventivos tienen fecha de creacion y fecha programada separadas; no entran en Mi jornada ni se asignan antes de esa fecha. Los antiguos conservan su fecha como programacion; la fecha real de creacion anterior no se puede reconstruir.
- Las alertas de reincidencia solo muestran correctivos repetidos: por si solas no demuestran mala calidad del mantenimiento.
- Los archivos de evidencia quedan referenciados por su ruta local, no copiados al sistema.

## Primera entrega: reglas y trazabilidad

- Revision del informe completo y apertura de evidencia antes del cierre.
- Asignacion manual y automatica validan especialidad y fecha programada.
- Creacion, asignacion, inicio, envio de informe, correccion y cierre dejan eventos con actor y fecha. Cada envio conserva el texto del informe en el historial.
- Rechazo de hallazgos y devolucion de informes requieren motivo. La aprobacion del hallazgo permite confirmar prioridad y especialidad, y enlaza el ticket generado.
- Cierre, evento y preventivo se guardan en una transaccion SQLite. El PDF se prepara temporalmente y se publica antes de confirmar la transaccion; errores ordinarios revierten el cierre. SQLite y el sistema de archivos no ofrecen una transaccion conjunta ante apagados abruptos.
- La base existente recibe columnas nuevas sin borrar tickets. Los eventos historicos anteriores no se inventan.
- Formularios con desplazamiento vertical para acceder a todas las acciones.
- El indicador de tiempo ahora indica que incluye la espera de validacion; aun no mide tiempo efectivo ni pausas.

Arquitectura minima para la demo:

- `dzone.py`: interfaz Tkinter y entrada del programa.
- `dzone_services.py`: reglas, transiciones y operaciones transaccionales.
- `dzone_core.py`: SQLite, datos iniciales, utilidades y PDF.
- `test_dzone.py`: pruebas aisladas con bases temporales.

Se mantiene el arranque con `py dzone.py`. Las entregas siguientes incorporaron login, rediseño visual y un motor local para la IA. Siguen pendientes la disponibilidad por turnos, las pausas y el almacenamiento de varias evidencias por ticket.

Pruebas: `py -m unittest -v test_dzone`. Incluyen un PDF real, fallos de PDF/base de datos, persistencia, migracion de la base anterior, restricciones de asignacion y revision de hallazgos.

## Segunda entrega: navegación e interfaz operativa

- Menú lateral con Inicio, Mi jornada, Tickets, Kanban, Validaciones, Hallazgos e Indicadores.
- Inicio con contadores navegables, accesos para crear/asignar y tickets que requieren atención.
- Jornada con tarjetas ordenadas por prioridad y acciones según el estado. Cambiar al rol Técnico abre Mi jornada.
- Tickets con búsqueda por código/actividad/equipo/responsable, filtros de estado/prioridad/técnico y apertura con doble clic o Enter.
- Bandeja de Validaciones para el supervisor, con acceso a informe, evidencia, corrección y cierre.
- Kanban sin límite de 15 tickets y con desplazamiento independiente por columna.
- Detalle con etapa actual destacada, motivo de corrección, consulta del reporte enviado y botones principales diferenciados.
- Tablas con mensajes para vistas vacías y formularios con botón de cierre visible. La actualización visual posterior usa desplazamiento de página con la rueda, sin barras visibles.
- Corregida la limpieza de vistas: Actualizar y cambiar de rol ya no destruyen la ventana principal.

Pruebas de reglas y ventanas: `py -m unittest -v test_dzone test_dzone_ui`. Se prueba también un flujo completo invocando los botones: crear → asignar → iniciar → enviar → validar → PDF, con una base temporal.

Vista de comprobación opcional: `py preview_dzone.py`. Carga datos temporales con un reporte por validar, trabajo iniciado y un hallazgo. Al cerrar se descartan esos datos; para conservar tu trabajo inicia siempre con `iniciar_windows.bat` o `py dzone.py`.

## Tercera entrega: borradores, micrófono e IA local

Modelo elegido: **Qwen3 4B Q4_K_M**, con motor CPU portátil llama.cpp. Voz: **Whisper base multilingüe** mediante faster-whisper. No se entrena ningún modelo ni se envían los reportes a una API externa. El motor de texto se inicia solo para la extracción, escucha en `127.0.0.1` y se detiene al terminar.

En un ticket **En proceso**:

1. Redacta manualmente o pulsa **Generar desde voz o texto**.
2. **Grabar micrófono** → **Detener y transcribir**. Revisa nombres, cifras y puntuación.
3. **Extraer con Qwen3 4B** clasifica referencias a oraciones originales. El programa copia esas oraciones, sin usar prosa nueva del modelo. No es una garantía de clasificación correcta: requiere revisión humana.
4. **Usar como borrador** lo lleva al editor. Puedes corregirlo y **Guardar borrador**, cerrar y retomarlo. El estado sigue siendo En proceso.
5. **Enviar reporte a validacion** abre una vista previa. Puedes volver y corregir; solo **Confirmar envío a supervisión** cambia el estado.

Se guardan revisiones, texto fuente, extracción, modelo y transcripción original vinculada al audio. **Ver versiones del borrador** permite consultar el historial. El PDF final se genera solo tras la validación del supervisor. La IA no crea automáticamente tickets desde los hallazgos extraídos.

Preparación desde código (Windows x64):

```cmd
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-ia.txt
.venv\Scripts\python.exe preparar_ia.py
.venv\Scripts\python.exe empaquetar_windows.py
```

`preparar_ia.py` usa Internet para descargar el modelo Qwen (aprox. 2,5 GB), Whisper y el motor CPU. Después, la inferencia es local. El motor se verifica contra SHA-256 publicado y el modelo contra metadatos oficiales. Las revisiones quedan en `modelos_manifest.json`.

El paquete es **toda la carpeta `dist/DzoneDemo`**, no un EXE aislado. Incluye Python, dependencias, modelos y licencias. El destinatario puede abrir `DzoneDemo.exe` sin instalar Python u Ollama. Cada máquina mantiene sus propios datos: enviar la aplicación no sincroniza tickets ni reportes. Consulta `LEEME_DISTRIBUCION.md`.

Pruebas completas: `.venv\Scripts\python.exe -m unittest -v test_dzone test_dzone_ai test_dzone_ui`.

Comprobación real de modelos/PDF/interfaz: `.venv\Scripts\python.exe dzone.py --verificar-paquete verificacion_local.json`. Usa datos temporales y un audio sintético en español incluido en `samples/`; nunca activa el micrófono real. La misma opción existe en el EXE para verificar la distribución.

Resultado de esta entrega: el EXE pasó la prueba con audio sintético en español, extracción real de Qwen3 4B, ventanas y PDF (`verificacion_ejecutable.json`). No se ha grabado el micrófono del usuario ni probado en otro computador. Para compartir se genera `dist/DzoneDemo_Windows_IA_local.zip`, con toda la carpeta de aplicación y modelos.

## Login y reinicio de prueba

`demo0` es supervisor; `demo1` y `demo3` son técnicos mecánicos, `demo2` eléctrico y `demo4` general. La contraseña coincide con el usuario. Las sesiones se validan en los servicios, incluso al llamar una acción que no está visible en el menú. Se rechazan acciones de supervisión desde cuentas técnicas y accesos a tickets o hallazgos de otros técnicos. Las contraseñas se guardan con PBKDF2-HMAC-SHA256 y sal por usuario.

La aplicación normal ya no crea tickets de ejemplo al arrancar. Solo `preview_dzone.py` y las pruebas solicitan explícitamente los cinco ejemplos en bases temporales.

Para reiniciar otra prueba, cierra Dzone y ejecuta `.venv\Scripts\python.exe reset_demo.py --reiniciar`. Guarda una copia consistente de SQLite y los documentos/audios anteriores en `.respaldos_demo/`, borra los registros de trabajo, reinicia identificadores y recrea las cinco cuentas. Conserva los modelos y la configuración de IA. No es una acción automática al abrir la aplicación ni al iniciar sesión.

Pruebas: `.venv\Scripts\python.exe -m unittest -v test_dzone test_dzone_ai test_dzone_auth test_dzone_ui`.

Verificación de esta actualización: 35 pruebas aprobadas y EXE comprobado con login de ambos roles, restricciones del técnico, voz sintética, Qwen3 y PDF. Evidencia: `verificacion_login_ejecutable.json`. El reinicio local dejó 0 tickets, 0 hallazgos y 0 borradores con las cinco cuentas listas; no vuelve a cargar ejemplos al abrir.

## Actualización visual y nuevos ejemplos

- Tablas con filas más amplias, encabezados suaves, selección índigo y tarjetas de resumen con una jerarquía visual más clara.
- Jornada y Kanban con tarjetas blancas, estados destacados y prioridades diferenciadas.
- Sin barras de desplazamiento visibles. La rueda del mouse desplaza la página desde títulos, tarjetas, tablas o el espacio alrededor. El Kanban avanza como una sola página, sin columnas con scroll independiente.
- El movimiento se detiene al soltar la rueda; no hay desplazamiento automático en reposo. AvPág/RePág permiten navegar con teclado; Shift + rueda sobre una tabla permite el desplazamiento horizontal si hace falta.
- Los campos de texto mantienen su propio desplazamiento mientras tengan contenido por recorrer; al llegar al límite continúa la página. Los formularios conservan el botón de cierre fijo.
- **IA y voz** aparece solo en el menú del supervisor. Los técnicos conservan los controles de voz y extracción dentro de sus tickets.
- **Cargar ejemplos** crea 12 tickets y los asigna según las reglas, sin duplicarlos al repetir. Solo actúa sobre los ejemplos, no asigna otros pendientes existentes. En esta prueba se cargaron 3 tickets para cada técnico demo1–demo4, todos en Asignado.

Los ejemplos de la base actual son datos ficticios solicitados para esta prueba. No se vuelven a crear al arrancar ni se insertan en el ZIP como una base personal. En otro equipo el supervisor puede pulsar Cargar ejemplos.

## Compilar EXE para Windows
Ejecutar en **Windows** (no compilacion cruzada desde Linux):

```cmd
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-ia.txt
.venv\Scripts\python.exe preparar_ia.py
.venv\Scripts\python.exe empaquetar_windows.py
```

Encontrarás `dist\DzoneDemo\DzoneDemo.exe`. Comparte toda la carpeta `DzoneDemo` con sus componentes y modelos. El EXE incluye Python y dependencias; los datos de trabajo se guardan fuera de la carpeta del programa. Consulta también `LEEME_DISTRIBUCION.md`.
