[English](./README.md) | **Español**

# Skills de aantars

Skills para agentes que uso en el día a día, empaquetadas para instalarlas en Claude Code, Codex o cualquier agente compatible con [Agent Skills](https://agentskills.io).

La primera es **video-to-html**: le das un vídeo (un enlace o un archivo de tu ordenador) y te devuelve una única página HTML autocontenida que puedes leer en lugar de verlo. Tú eliges el formato: tutorial paso a paso, lo más destacado o un resumen completo, en el idioma que quieras, con tema claro y oscuro y capturas sacadas del propio vídeo.

**confluence-read** lee una página de Confluence completa: el texto a través de tu servidor MCP de Confluence y, además, las capturas, los diagramas y los adjuntos que un wiki con 2FA deja fuera de su alcance. Guarda la cookie de 2FA con su fecha de caducidad y te avisa cuando hay que renovarla. Irán llegando más skills.

## Instalación

Instala las skills (paso 1). `video-to-html` necesita además la skill `watch`, en la que se apoya (paso 2); `confluence-read` no necesita ninguna otra skill.

Un plugin es un paquete gestionado al que te suscribes. [skills.sh](https://skills.sh) copia archivos editables en la carpeta de skills de tu agente, y las actualizaciones corren de tu cuenta. **Elige una sola vía por agente**: si instalas las dos, tendrás cada skill duplicada.

### 1. Instala la skill

<details>
<summary><strong>Claude Code (CLI)</strong></summary>

```bash
claude plugin marketplace add bradautomates/claude-video
claude plugin marketplace add aantars/skills
claude plugin install aantars-skills@aantars
```

El plugin declara `watch@claude-video` como dependencia, así que al instalarlo se instala también `watch`. Para que funcione hay que añadir antes el marketplace `claude-video`; con esto puedes saltarte el paso 2.

</details>

<details>
<summary><strong>Claude Code (dentro de una sesión)</strong></summary>

```text
/plugin marketplace add bradautomates/claude-video
/plugin marketplace add aantars/skills
/plugin install aantars-skills@aantars
```

Después ejecuta `/reload-plugins` o abre una sesión nueva. `watch` se instala como dependencia; sáltate el paso 2.

</details>

<details>
<summary><strong>Claude Desktop (pestaña Code)</strong></summary>

1. Abre **Customize**, selecciona **Plugins** y luego **Add** > **Add marketplace**.
2. Añade `bradautomates/claude-video` y después `aantars/skills`.
3. Busca **aantars-skills** en la lista e instálalo. `watch` debería instalarse con él; si no aparece como instalado, instala también **watch**.
4. Úsalo desde una sesión de **Code** (no desde Chat ni Cowork).

</details>

<details>
<summary><strong>Codex</strong></summary>

```bash
codex plugin marketplace add aantars/skills
codex plugin add aantars-skills@aantars
```

Después abre una sesión nueva de Codex.

</details>

<details>
<summary><strong>Cualquier otro agente</strong> (skills.sh, actualización manual)</summary>

```bash
npx skills@latest add aantars/skills --skill video-to-html
npx skills@latest add aantars/skills --skill confluence-read
```

Ejecuta solo las líneas de las skills que quieras. Elige tu agente cuando te lo pregunte (o indícalo con `-a <agente>`). Para actualizar, ejecuta `npx skills@latest update`.

</details>

### 2. Instala la dependencia `watch` (obligatorio)

`video-to-html` usa la skill `watch` de [bradautomates/claude-video](https://github.com/bradautomates/claude-video) para descargar el vídeo, obtener la transcripción y extraer fotogramas. Sin ella no funciona. Con el plugin de Claude Code ya se instala en el paso 1; en Codex y otros agentes, instálala aquí. Los comandos de Claude Code de abajo sirven para instalarla por separado.

<details>
<summary><strong>Claude Code (CLI)</strong></summary>

```bash
claude plugin marketplace add bradautomates/claude-video
claude plugin install watch@claude-video
```

</details>

<details>
<summary><strong>Claude Code (dentro de una sesión)</strong></summary>

```text
/plugin marketplace add bradautomates/claude-video
/plugin install watch@claude-video
```

</details>

<details>
<summary><strong>Claude Desktop (pestaña Code)</strong></summary>

**Customize** > **Plugins** > **Add** > **Add marketplace**, escribe `bradautomates/claude-video` e instala **watch**.

</details>

<details>
<summary><strong>Codex</strong></summary>

```bash
codex plugin marketplace add bradautomates/claude-video
codex plugin add watch@claude-video
```

</details>

<details>
<summary><strong>Cualquier otro agente</strong></summary>

```bash
npx skills@latest add bradautomates/claude-video -g --skill watch
```

</details>

`watch` necesita Python 3.10 o superior, ffmpeg y yt-dlp; su configuración inicial comprueba que estén y te ayuda a instalar lo que falte. Para vídeos sin subtítulos hace falta además un método de transcripción alternativo: una clave de API de Groq u OpenAI, o WhisperX en local. `watch` no funciona en el chat de Claude ni en Cowork, solo en Claude Code, Codex y otros agentes que se ejecutan en tu equipo.

Si te saltas este paso, no pasa nada: `video-to-html` comprueba si `watch` está instalada antes de empezar y se ofrece a instalarla por ti.

### 3. Primer uso

Ejecuta `/watch` una vez con cualquier vídeo corto, o pide directamente `video-to-html`: se encarga de lanzar la configuración inicial de `watch`. Si vas a convertir vídeos sin subtítulos, ten a mano una clave de API de Groq para cuando la configuración te pida un método de transcripción alternativo (o elige WhisperX en local).

Luego prueba con algo como: *"Convierte este vídeo en un tutorial: https://www.youtube.com/watch?v=..."*

## Referencia

Las skills **invocadas por el modelo** puedes lanzarlas tú escribiendo su nombre (`/video-to-html`) o el agente las usa por su cuenta cuando tu petición encaja.

### Productividad

Herramientas para el trabajo diario, no específicas de programación.

**Invocadas por el modelo**

- **[video-to-html](./skills/productivity/video-to-html/SKILL.md)**: Convierte un vídeo (URL o archivo local) en una única página HTML autocontenida y adaptable, con tema claro y oscuro: un tutorial paso a paso, un resumen de lo más destacado o un resumen completo de todos los temas. [Documentación](./docs/productivity/video-to-html.es.md)
- **[confluence-read](./skills/productivity/confluence-read/SKILL.md)**: Lee una página de Confluence (Server / Data Center) completa, incluidas las imágenes y los adjuntos protegidos por 2FA: el texto desde tu servidor MCP de Confluence y los archivos mediante una cookie de 2FA guardada que te avisa cuando caduca. [Documentación](./docs/productivity/confluence-read.es.md)

## Actualizar y desinstalar

| Vía | Actualizar | Desinstalar |
| --- | --- | --- |
| Claude Code | `claude plugin marketplace update aantars` y después `claude plugin update aantars-skills@aantars`. O activa la actualización automática del marketplace `aantars` en `/plugin` > **Marketplaces**. | `claude plugin uninstall aantars-skills@aantars` y después `claude plugin marketplace remove aantars` |
| Claude Desktop | **Customize** > **Plugins**, abre **aantars-skills** y actualízalo | En el mismo sitio, desinstálalo |
| Codex | Se actualiza solo al arrancar | Quita **aantars-skills** desde el navegador de `/plugins` |
| skills.sh | `npx skills@latest update` | `npx skills@latest remove <nombre-de-la-skill>`, por ejemplo `video-to-html` |

`watch` se actualiza y se desinstala igual, con `watch@claude-video` y el marketplace `claude-video`.

## Licencia

[MIT](./LICENSE)
