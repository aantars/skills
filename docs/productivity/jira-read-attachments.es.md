## Qué hace

`jira-read-attachments` lee una incidencia de Jira como lo haría una persona: los campos, la descripción y los comentarios, y también las capturas, los logs y los archivos adjuntos (PDF, XML, patches) que la explican. Todo pasa por un pequeño script incluido que llama a la API REST de Jira con la cookie de sesión de tu navegador, así que funciona donde un servidor MCP no puede descargar adjuntos.

La cookie de sesión nunca pasa por el chat. La guardas una vez, en tu propia terminal, con el script incluido. Se conserva (cifrada con tu cuenta de Windows, si usas Windows) y el agente solo llega a saber si es válida, si ha caducado o si Jira la ha rechazado.

## Cuándo usarla

Escribe `/jira-read-attachments`, o el agente la usa por su cuenta cuando compartes un enlace o una clave de incidencia de Jira y quieres que lea sus adjuntos o imágenes, mencionas la cookie de sesión de Jira, o falla la descarga de un adjunto con el MCP de Jira. Para un resumen rápido de solo texto, usa un lector de Jira sencillo.

Cada vez te pregunta qué leer además del texto:

| Eliges | Lee |
| --- | --- |
| **Imágenes** | Capturas, cada una relacionada con la descripción o el comentario que la menciona |
| **Adjuntos** | PDF, XML, logs, patches, SQL y demás archivos adjuntos |
| **Ambos** | Todo lo anterior |
| **Solo texto** | Solo el texto de la incidencia; no descarga nada |

Si la incidencia tiene muchos adjuntos, después te pregunta cuáles importan para tu pregunta y descarga solo esos.

## Requisitos

- **Jira Server o Data Center.** Jira Cloud sirve los adjuntos desde otro dominio que una cookie de sesión no abre.
- **Python 3.10+.** El script solo usa la biblioteca estándar.
- Un agente que se ejecute en tu ordenador: Claude Code (terminal, VS Code o la pestaña **Code** de Claude Desktop), Codex u otro agente local.

## La cookie

La primera vez que pides una incidencia, o cuando la cookie guardada deja de funcionar, el agente te explica el motivo y te da un único comando para ejecutar en tu terminal. Ese comando te indica cómo copiar la cookie desde las herramientas de desarrollo del navegador (la cabecera `Cookie` completa de la pestaña Network, o solo `JSESSIONID`), te la pide oculta mientras la pegas, te pide una fecha de caducidad opcional, la prueba contra Jira y la guarda en `~/.jira-read/cookies.json`.

| Estado de la cookie | Qué pasa |
| --- | --- |
| Válida | Nada que decir; lee la incidencia |
| Caduca en menos de un día | Una línea con la fecha y lee |
| Caducada, inexistente o rechazada por Jira | Se detiene, te dice por qué y te da el comando para renovarla |

Una sesión de Jira suele terminar en el servidor (por inactividad o al cerrar sesión), así que "rechazada" es el estado que más verás. El script lo registra, así que la siguiente sesión ya lo sabe. La cookie solo se envía a tu servidor de Jira.

## Preguntas frecuentes

**¿Por qué no pegar la cookie directamente en el chat?**
Porque es una sesión activa: quien la tenga entra como tú. Pegada en el chat, se queda en el historial de la conversación. Escrita en tu propia terminal, va directa al almacén cifrado. Si la pegas igualmente, el agente no la usará y te sugerirá cerrar sesión en Jira para invalidarla.

**¿Puede modificar mis incidencias?**
No. El script solo lee.

**¿Dónde van los archivos descargados?**
A una carpeta temporal que se borra al terminar la respuesta, salvo que pidas guardarlos en algún sitio.

## Funciona bien si

- Obtienes respuestas sobre lo que aparece en las capturas de una incidencia y en sus archivos adjuntos, no solo sobre su texto.
- Solo te pide la cookie cuando falta, ha caducado o ha sido rechazada, y nunca te pide que la pegues en el chat.
- No quedan archivos descargados por ahí, salvo que pidieras guardarlos.

## Dónde encaja

Una herramienta independiente para leer incidencias de Jira. Complementa a un servidor MCP de Jira como [mcp-atlassian](https://github.com/sooperset/mcp-atlassian), que se ocupa del texto, la búsqueda y la edición, y va junto a [confluence-read](https://github.com/aantars/skills/blob/main/skills/productivity/confluence-read/SKILL.md), que hace lo mismo con las páginas del wiki.
