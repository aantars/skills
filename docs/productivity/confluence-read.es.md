## Qué hace

`confluence-read` lee una página de Confluence como lo haría una persona: el texto y también las capturas, los diagramas y los archivos adjuntos (PDF, XML, patches, SQL) que lo explican. El texto llega a través de tu servidor MCP de Confluence; las imágenes y los adjuntos, a través de un pequeño script incluido, porque en un wiki protegido con un plugin de 2FA esas descargas necesitan una cookie del navegador que los servidores MCP no tienen.

La cookie de 2FA nunca pasa por el chat. La guardas una vez, en tu propia terminal, con el script incluido. Se conserva junto con su fecha de caducidad (cifrada con tu cuenta de Windows, si usas Windows) y el agente solo llega a saber si es válida, si está a punto de caducar, si ha caducado o si el wiki la ha rechazado.

## Cuándo usarla

Escribe `/confluence-read`, o el agente la usa por su cuenta cuando compartes un enlace a una página de Confluence, le pides que lea, revise o resuma una página del wiki, o quieres saber qué muestran sus capturas o sus adjuntos.

Cada vez te pregunta qué leer además del texto:

| Eliges | Lee |
| --- | --- |
| **Imágenes** | Capturas y diagramas, cada uno relacionado con la sección de la página que ilustra |
| **Adjuntos** | PDF, XML, patches, SQL y demás archivos adjuntos a la página |
| **Ambos** | Todo lo anterior |
| **Solo texto** | Solo el texto; no comprueba ni menciona la cookie |

Si la página tiene muchos adjuntos, después te pregunta cuáles importan para tu pregunta y descarga solo esos.

## Requisitos

- **Confluence Server o Data Center.** Confluence Cloud no usa esta cookie de 2FA.
- **Un servidor MCP de Confluence** para el texto, como [mcp-atlassian](https://github.com/sooperset/mcp-atlassian). Si no lo tienes, el script exporta el texto él mismo, en Markdown.
- **Un Personal Access Token** (en Confluence: Perfil > Personal Access Tokens), guardado en `~/.confluence_token` o en la variable de entorno `CONFLUENCE_TOKEN`.
- **Python 3.10+.** El script solo usa la biblioteca estándar.
- Un agente que se ejecute en tu ordenador: Claude Code (terminal, VS Code o la pestaña **Code** de Claude Desktop), Codex u otro agente local.

## La cookie y su fecha de caducidad

La primera vez que pides imágenes o adjuntos, o cuando la cookie guardada deja de funcionar, el agente te explica el motivo y te da un único comando para ejecutar en tu terminal. Ese comando te indica dónde encontrar `Confluence_2FASessionVerified` en las herramientas de desarrollo del navegador, te pide su valor (oculto mientras lo pegas), te pide su fecha de caducidad (la columna **Expires / Max-Age**), la prueba contra la página y guarda las dos cosas en `~/.confluence-read/cookies.json`.

A partir de ahí, antes de descargar nada, el agente revisa la fecha guardada. Solo te habla de la cookie cuando hace falta:

| Estado de la cookie | Qué pasa |
| --- | --- |
| Válida | Nada que decir; descarga |
| Caduca en menos de un día | Una línea con la fecha y descarga |
| Caducada, inexistente o rechazada por el wiki | Se detiene, te dice por qué y te da el comando para renovarla |

"Rechazada" cubre el caso de una cookie que el wiki no acepta antes de su fecha, por ejemplo después de cerrar sesión. El script también lo registra, así que la siguiente sesión ya lo sabe.

## Preguntas frecuentes

**¿Por qué no pegar la cookie directamente en el chat?**
Porque es una sesión activa y ya verificada: quien la tenga entra como tú, saltándose la 2FA. Pegada en el chat, se queda en el historial de la conversación. Escrita en tu propia terminal, va directa al almacén cifrado.

**¿Cada cuánto hay que renovarla?**
Cada vez que tu wiki te obligue a volver a entrar con 2FA; la fecha de caducidad de las herramientas de desarrollo te lo dice. Renovarla lleva un minuto.

**¿Dónde van los archivos descargados?**
A una carpeta temporal que se borra al terminar la respuesta, salvo que pidas guardarlos en algún sitio.

**¿Funciona con cualquier Confluence?**
Está pensada para Server y Data Center con un plugin de 2FA que crea `Confluence_2FASessionVerified`. Sin 2FA también funciona: las descargas salen bien solo con el token.

## Funciona bien si

- Obtienes respuestas sobre lo que aparece en las capturas de una página, no solo sobre su texto.
- Solo te pide la cookie cuando falta, ha caducado o ha sido rechazada, y nunca te pide que la pegues en el chat.
- Después de renovarla, la siguiente sesión descarga las imágenes sin preguntarte nada.
- No quedan archivos descargados por ahí, salvo que pidieras guardarlos.

## Dónde encaja

Una herramienta independiente para leer páginas del wiki. Complementa a un servidor MCP de Confluence como [mcp-atlassian](https://github.com/sooperset/mcp-atlassian): el servidor se ocupa del texto, la búsqueda y la edición; `confluence-read` añade las imágenes y los adjuntos que el servidor no puede descargar.
