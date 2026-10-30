# Dzone · demo local para Windows

1. Copia y descomprime la carpeta completa `DzoneDemo` en el equipo.
2. Ejecuta `DzoneDemo.exe`. No necesitas instalar Python ni Ollama. Inicia sesión con **demo0 / demo0** (supervisor).
3. En **IA y voz** comprueba que motor, Qwen3 4B y modelo de voz estén disponibles. Puedes crear un ticket o pulsar **Cargar ejemplos** para disponer de 12 ya asignados, sin duplicarlos al repetir.
4. Selecciona especialidad Mecánica para probar con demo1 y pulsa **Asignar pendientes**. Revisa el responsable, **cierra sesión** e ingresa con ese usuario y la misma contraseña (por ejemplo **demo1 / demo1**). No hay selector de roles dentro de la sesión.
5. Inicia el trabajo. Pulsa **Generar desde voz o texto**.
6. Pulsa **Grabar micrófono**, habla y pulsa **Detener y transcribir**. Se usa la entrada de audio predeterminada de Windows.
7. Revisa la transcripción. Pulsa **Extraer con Qwen3 4B** y revisa las citas organizadas.
8. Pulsa **Usar como borrador**, corrige el reporte y pulsa **Guardar borrador**. Puedes cerrar y retomarlo después.
9. **Enviar reporte a validacion** abre una vista previa. **Volver y corregir** permite editar. Solo **Confirmar envío a supervisión** lo entrega al supervisor.
10. Cierra sesión y vuelve con **demo0 / demo0**. El supervisor puede devolverlo con motivo o validar el cierre y generar el PDF final.

## Cuentas de prueba

| Usuario | Contraseña | Permisos / especialidad |
|---|---|---|
| demo0 | demo0 | Supervisor: crear, asignar, revisar hallazgos y validar cierres |
| demo1 | demo1 | Técnico de Mecánica |
| demo2 | demo2 | Técnico de Electricidad |
| demo3 | demo3 | Técnico de Mecánica |
| demo4 | demo4 | Técnico General |

Cada técnico ve únicamente sus tickets y hallazgos. No puede crear/asignar tickets, validar cierres ni revisar hallazgos de otros. El supervisor no redacta ni inicia el trabajo en nombre de un técnico. Las contraseñas están guardadas como hashes con sal, pero son credenciales públicas y sencillas elegidas para la demo.

## Navegación actualizada

La navegación entre secciones se realiza únicamente desde el menú lateral, sin una segunda fila de pestañas debajo de Cerrar sesión.

La interfaz usa tablas y tarjetas de lectura amplia. No muestra barras de desplazamiento: gira la rueda del mouse sobre la página, incluso fuera de la tabla. El movimiento se detiene al dejar de usarla. En el Kanban se desplaza toda la página, no una columna aislada. También puedes usar AvPág/RePág y Shift + rueda para desplazarte horizontalmente en una tabla. La configuración de IA está solo en supervisión; el técnico usa voz e IA desde sus tickets.

La extracción usa citas del texto de origen: no agrega mediciones ni actividades. Eso no garantiza que la transcripción sea correcta ni que lo narrado haya ocurrido; el técnico y el supervisor deben revisarlo. Los datos ausentes quedan como **No informado**. Los hallazgos extraídos son texto del borrador: no se crean ni aprueban tickets automáticamente.

## Equipo y funcionamiento

- Windows x64 y CPU compatible con el motor incluido. Se recomienda probar con 16 GB de RAM y espacio suficiente para el paquete, los modelos y los documentos. La velocidad varía según CPU y memoria disponible; no se garantiza el mismo rendimiento en todos los equipos.
- CPU como configuración inicial: no exige GPU dedicada. Debe validarse en cada equipo destinatario.
- Micrófono configurado y permiso de Windows para aplicaciones de escritorio. La aplicación no cambia esos permisos.
- No se graba hasta que el usuario pulsa Grabar. Máximo de cinco minutos por grabación.
- Modelos incluidos: Qwen3 4B Q4_K_M y Whisper Tiny multilingüe mediante faster-whisper (CPU, int8). No se entrenan con tus documentos.
- La inferencia no requiere Internet una vez copiados todos los archivos. La comunicación del motor es únicamente con `127.0.0.1` en el mismo equipo. No hay servidor compartido ni sincronización entre usuarios.

## Qué carpeta enviar

Envía **toda** la carpeta `dist/DzoneDemo`, incluidos `_internal`, `runtime`, `models`, `licenses` y el EXE. No envíes solo el ejecutable. No necesitas enviar el proyecto, `.venv`, cachés ni carpetas con bases y grabaciones. Los modelos hacen que el paquete ocupe varios GB.

Cada equipo guarda sus propios tickets, versiones, PDFs y audios en `%LOCALAPPDATA%/DzoneDemo/`. Compartir el programa no comparte ni sincroniza esos datos. Guarda una copia de esa carpeta para respaldarlos.

La configuración se guarda en `ia.json` dentro de esa carpeta de datos. Si moviste rutas manualmente, vuelve a seleccionarlas en **IA y voz**. Los errores del motor se registran en `motor_ia.log`; los de interfaz en `errores.log`.

Esta es una demo con login local y cuentas de prueba conocidas, sin firma digital. No incluye activación por licencia. Si por “activar” se requiere una licencia comercial por equipo, eso es una función adicional.

## Verificación realizada

El EXE fue comprobado en el equipo de desarrollo con un audio sintético en español: transcripción local, extracción de campos con Qwen3 4B, carga/actualización de ventanas y generación del PDF. Esa muestra tardó aproximadamente 3 segundos en voz y 9 en extracción. Es una muestra corta, no una garantía de rendimiento. La grabación con micrófono real y la compatibilidad en otra máquina requieren una prueba del destinatario.
