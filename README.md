**English** | [Español](./README.es.md)

# aantars skills

Agent skills I use for everyday work, packaged so you can install them in Claude Code, Codex or any agent that reads [Agent Skills](https://agentskills.io).

The first one is **video-to-html**: give it a video (a link or a file on your computer) and it writes one self-contained HTML page you can read instead of watching. You choose a step-by-step tutorial, the highlights, or a full summary, in any language, with light and dark themes and screenshots taken from the video itself.

**confluence-read** reads a Confluence page in full: the text through your Confluence MCP server, plus the screenshots, diagrams and attachments that a wiki behind 2FA keeps out of reach. It stores the 2FA cookie with its expiry date and tells you when it needs renewing. More skills will follow.

## Installation

Install the skills (step 1). `video-to-html` also needs the `watch` skill it is built on (step 2); `confluence-read` needs no other skill.

A plugin is a managed bundle you subscribe to. [skills.sh](https://skills.sh) copies editable files into your agent's skills folder, and you update them yourself. **Pick one per agent**: installing both gives you every skill twice.

### 1. Install the skill

<details>
<summary><strong>Claude Code (CLI)</strong></summary>

```bash
claude plugin marketplace add bradautomates/claude-video
claude plugin marketplace add aantars/skills
claude plugin install aantars-skills@aantars
```

The plugin declares `watch@claude-video` as a dependency, so the install also brings in `watch`. Adding the `claude-video` marketplace first is what makes that possible; skip step 2.

</details>

<details>
<summary><strong>Claude Code (in a session)</strong></summary>

```text
/plugin marketplace add bradautomates/claude-video
/plugin marketplace add aantars/skills
/plugin install aantars-skills@aantars
```

Then run `/reload-plugins` or start a new session. `watch` comes along as a dependency; skip step 2.

</details>

<details>
<summary><strong>Claude Desktop (Code tab)</strong></summary>

1. Open **Customize**, select **Plugins**, then **Add** > **Add marketplace**.
2. Add `bradautomates/claude-video`, then add `aantars/skills`.
3. Find **aantars-skills** in the list and install it. `watch` should be installed with it; if it is not listed as installed, install **watch** too.
4. Use it from a **Code** session (not Chat or Cowork).

</details>

<details>
<summary><strong>Codex</strong></summary>

```bash
codex plugin marketplace add aantars/skills
codex plugin add aantars-skills@aantars
```

Start a new Codex session afterwards.

</details>

<details>
<summary><strong>Any other agent</strong> (skills.sh, manual updates)</summary>

```bash
npx skills@latest add aantars/skills --skill video-to-html
npx skills@latest add aantars/skills --skill confluence-read
```

Run only the lines for the skills you want. Pick your agent when prompted (or pass `-a <agent>`). To update, run `npx skills@latest update`.

</details>

### 2. Install the `watch` dependency (required)

`video-to-html` uses the `watch` skill from [bradautomates/claude-video](https://github.com/bradautomates/claude-video) to download the video, pull the transcript and extract frames. It will not run without it. With the Claude Code plugin it is installed in step 1; on Codex and other agents, install it here. The Claude Code commands below are for installing it on its own.

<details>
<summary><strong>Claude Code (CLI)</strong></summary>

```bash
claude plugin marketplace add bradautomates/claude-video
claude plugin install watch@claude-video
```

</details>

<details>
<summary><strong>Claude Code (in a session)</strong></summary>

```text
/plugin marketplace add bradautomates/claude-video
/plugin install watch@claude-video
```

</details>

<details>
<summary><strong>Claude Desktop (Code tab)</strong></summary>

**Customize** > **Plugins** > **Add** > **Add marketplace**, enter `bradautomates/claude-video`, then install **watch**.

</details>

<details>
<summary><strong>Codex</strong></summary>

```bash
codex plugin marketplace add bradautomates/claude-video
codex plugin add watch@claude-video
```

</details>

<details>
<summary><strong>Any other agent</strong></summary>

```bash
npx skills@latest add bradautomates/claude-video -g --skill watch
```

</details>

`watch` needs Python 3.10+, ffmpeg and yt-dlp; its first-run setup checks them and helps you install what is missing. Videos without captions also need a transcription fallback: a Groq or OpenAI API key, or local WhisperX. `watch` does not work in Claude chat or Cowork, only in Claude Code, Codex and other local agent hosts.

If you forget this step, no harm done: `video-to-html` checks for `watch` before it starts and offers to install it for you.

### 3. First run

Run `/watch` once on any short video, or just ask for `video-to-html`: it runs `watch`'s first-run setup for you. If you plan to convert videos without captions, have a Groq API key ready when the setup asks for a transcription fallback (or pick local WhisperX).

Then try something like: *"Turn this video into a tutorial: https://www.youtube.com/watch?v=..."*

## Reference

**Model-invoked** skills can be typed by you (`/video-to-html`) or picked up by the agent on its own when your request fits.

### Productivity

Everyday workflow tools, not code-specific.

**Model-invoked**

- **[video-to-html](./skills/productivity/video-to-html/SKILL.md)**: Turn a video (URL or local file) into one self-contained, responsive HTML page with light and dark themes: a step-by-step tutorial, a highlights summary, or a full summary of every topic covered. [Docs](./docs/productivity/video-to-html.md)
- **[confluence-read](./skills/productivity/confluence-read/SKILL.md)**: Read a Confluence (Server / Data Center) page in full, including the images and attachments behind a 2FA wall: text from your Confluence MCP server, files through a stored 2FA cookie that warns you when it has expired. [Docs](./docs/productivity/confluence-read.md)

## Updating and uninstalling

| Route | Update | Uninstall |
| --- | --- | --- |
| Claude Code | `claude plugin marketplace update aantars`, then `claude plugin update aantars-skills@aantars`. Or turn on auto-update for the `aantars` marketplace in `/plugin` > **Marketplaces**. | `claude plugin uninstall aantars-skills@aantars`, then `claude plugin marketplace remove aantars` |
| Claude Desktop | **Customize** > **Plugins**, open **aantars-skills** and update it | Same place, uninstall it |
| Codex | Updates itself at startup | Remove **aantars-skills** from the `/plugins` browser |
| skills.sh | `npx skills@latest update` | `npx skills@latest remove <skill-name>`, for example `video-to-html` |

`watch` updates and uninstalls the same way, with `watch@claude-video` and the `claude-video` marketplace.

## License

[MIT](./LICENSE)
