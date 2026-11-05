## Qué hace

`video-to-html` convierte un vídeo en una página HTML que puedes leer en lugar de verlo. Le das un enlace o un archivo de tu ordenador y obtienes un único archivo autocontenido: adaptable a cualquier pantalla, con tema claro y oscuro, un índice que funciona, capturas incrustadas en la propia página y marcas de tiempo que te llevan al momento exacto del vídeo. Puedes abrirlo sin conexión, mandarlo por correo o dejarlo en una carpeta compartida.

Trabaja con **las pruebas por delante**: cada frase sale de la transcripción y cada imagen de un fotograma que el agente ha mirado de verdad. No rellena huecos con conocimiento general ni describe lo que el vídeo "probablemente" muestra. Si algo no queda claro en el vídeo, la página lo dice o lo deja fuera.

## Cuándo usarla

Escribe `/video-to-html`, o deja que el agente la use por su cuenta cuando le pidas convertir, documentar, resumir o pasar a limpio un vídeo, sacar una guía de una grabación o extraer lo importante de una charla, un webinar, una demo o una reunión.

Genera uno de estos tres tipos de página:

| Quieres | Elige | Qué obtienes |
| --- | --- | --- |
| Reproducir lo que se ve en el vídeo | **Tutorial** | Pasos numerados, una acción por paso, con valores exactos, rutas de menú y comandos, una captura por cada paso que cambia la pantalla y los errores habituales |
| Quedarte solo con lo que merece la pena | **Lo más destacado** | Los momentos más útiles o sorprendentes, ordenados por interés y no por tiempo, a menudo con una cita |
| Tener constancia de todo lo que se trató | **Resumen completo** | Todos los temas en el orden del vídeo, cada uno con su idea principal, los puntos que la apoyan y las conclusiones |

Si lo dejas en **Automático**, elige Tutorial para los vídeos de "cómo se hace" y Resumen completo para el resto, y te dice cuál ha elegido.

## Requisitos

- La skill **`watch`** de [bradautomates/claude-video](https://github.com/bradautomates/claude-video). Es la que descarga el vídeo, obtiene la transcripción y extrae los fotogramas. `video-to-html` comprueba primero si está instalada y, si falta, se ofrece a instalarla; tienes los comandos en el [README](https://github.com/aantars/skills/blob/main/README.es.md#2-instala-la-dependencia-watch-obligatorio).
- **Python 3.10 o superior**, **ffmpeg** y **yt-dlp** en tu equipo. La configuración inicial de `watch` comprueba que estén y te ayuda a instalar lo que falte.
- Para vídeos **sin subtítulos**: un método de transcripción alternativo en `watch` (una clave de API de Groq u OpenAI, o WhisperX en local). Sin él, la página se construye solo con lo que se ve y queda más pobre.
- Un agente que se ejecute en tu ordenador: Claude Code (terminal, VS Code o la pestaña **Code** de Claude Desktop), Codex u otro agente local.

Todo lo guarda en una carpeta nueva dentro del directorio actual, con el nombre `AAAA-MM-DD_<slug>/`.

## Cómo es una ejecución

**Por defecto o a medida.** Lo primero que pregunta es si aceptas la configuración por defecto (tipo automático, tu idioma, detalle estándar, vídeo completo) o prefieres personalizarla. Si personalizas, eliges el tipo, el idioma de la página, el nivel de detalle (Conciso, Estándar o Detallado) y extras como un glosario, marcas de tiempo clicables, solo un tramo del vídeo o imágenes más grandes para vídeos llenos de código o texto pequeño.

**Estimación de escenas.** Antes de mirar ningún fotograma, mide cuánto cambia la imagen a lo largo del vídeo y te enseña una tabla breve:

| Valor | Qué te dice |
| --- | --- |
| Duración | La longitud del tramo que se va a analizar |
| Cambios de escena (sensible / estándar / grande) | Cuántas veces cambia la imagen: cambios pequeños, como una línea nueva de código, o solo los grandes, como una diapositiva nueva |
| Línea de tiempo | Un minigráfico de cambios por minuto; las barras altas marcan dónde se concentra la acción |
| Vídeo estático | Si casi todo el rato se ve lo mismo (alguien hablando a cámara, una sola diapositiva); en ese caso el contenido lo lleva la transcripción |
| Presupuestos (ligero / equilibrado / exhaustivo) | Cuántos fotogramas se van a analizar, con un coste aproximado en tokens de imagen |

Te recomienda un presupuesto (normalmente el equilibrado) y espera a que lo confirmes, junto con el tramo a analizar.

**Anonimización.** Te pregunta si hay algo que difuminar: una zona fija, como la imagen de la webcam o la barra de direcciones (antes ves una vista previa), datos sensibles que detecta solo, como correos, nombres, tokens o caras (apruebas la lista antes de que se difumine nada), las dos cosas o nada.

**El trabajo en sí.** El vídeo se divide en unos pocos tramos y cada uno lo procesa un [subagente](https://www.aihero.dev/ai-coding-dictionary/subagent) con una [ventana de contexto](https://www.aihero.dev/ai-coding-dictionary/context-window) limpia, para que los fotogramas de una parte no desplacen al resto. Después se unen las piezas en una sola página, se comprueba que no haya enlaces rotos ni imágenes que falten, y se genera el archivo final.

**Conservar o borrar el vídeo, y limpieza.** Con los vídeos en línea, eliges al principio si quieres guardar el archivo descargado junto a la página o borrarlo. En cualquier caso, al terminar se eliminan todos los archivos de trabajo (fotogramas, transcripción, borradores). Si le pasas un vídeo de tu equipo, nunca lo mueve, lo modifica ni lo borra.

## Preguntas frecuentes

**¿Cuánto cuesta una ejecución?**
Casi todo el coste son imágenes. Cada fotograma analizado con el ancho por defecto ronda los 800 tokens de imagen, así que una ejecución equilibrada sobre una grabación de pantalla con mucho movimiento puede llegar a decenas de miles de tokens, mientras que un vídeo de alguien hablando a cámara necesita solo unos pocos fotogramas. La estimación de escenas te enseña el cálculo antes de analizar ningún fotograma, y siempre puedes bajar al presupuesto ligero o acotar un tramo más corto.

**¿Funciona en el chat de Claude o en Cowork?**
No. `watch` necesita descargar y procesar el vídeo con herramientas de tu equipo, así que solo funciona en Claude Code, Codex y otros agentes que se ejecutan en local.

**¿Sirve para vídeos privados o internos?**
Con un enlace, solo puede descargar lo que yt-dlp alcance desde tu equipo. Si es una grabación privada, descárgala tú y dale al agente la ruta del archivo. El vídeo y los fotogramas se procesan en local; la única excepción es la transcripción en la nube (Groq u OpenAI), que envía el audio a ese proveedor. Si eso te preocupa, usa WhisperX en local.

**¿La página puede estar en otro idioma que el vídeo?**
Sí. El idioma de la página se elige aparte: el tuyo, el del vídeo, inglés o cualquier otro. Los títulos, las etiquetas y el índice lo siguen.

**¿Y los vídeos largos?**
Funcionan, pero el coste crece con la duración. El vídeo se divide en tramos de unos minutos que se procesan en paralelo, así que una charla de una hora no es problema. Si de un vídeo largo solo te interesa una parte, elige **Solo un tramo** y se salta el resto.

## Funciona bien si

- Cada captura muestra algo a lo que se refiere el texto, y su pie te dice en qué fijarte.
- Siguiendo una página de tipo Tutorial paso a paso consigues lo mismo que en el vídeo, sin haberlo visto.
- Las marcas de tiempo te llevan al momento correcto del vídeo original.
- La página se lee bien en modo claro, en modo oscuro y en el móvil, sin desplazamiento lateral.
- En la carpeta de salida solo queda el HTML (y el vídeo, si elegiste conservarlo): ni fotogramas ni borradores sueltos.

## Dónde encaja

Es una herramienta independiente a la que recurres cada vez que un vídeo tiene que convertirse en algo que la gente pueda leer, buscar y compartir. Se apoya en [watch](https://github.com/bradautomates/claude-video), que responde preguntas sobre un vídeo dentro de la conversación; `video-to-html` convierte esas mismas pruebas en un documento duradero.
