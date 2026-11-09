# The canonical install block

One install story, one wording. `README.md` and `README.es.md` must say **this** and nothing else (the Spanish README carries the same commands with translated prose). Change it here first, then propagate to both READMEs in the same change.

## Routes

This repo is its own marketplace: `.claude-plugin/marketplace.json` (marketplace `aantars`) lists one plugin, `aantars-skills`, whose `plugin.json` ships every promoted skill. It is not in `claude-plugins-official`, so every plugin route starts by adding the `aantars/skills` marketplace. Plugin routes reinstall only when the `version` in `plugin.json` changes: bump it on every release.

| Agent | Route | Updates itself? |
| --- | --- | --- |
| Claude Code (CLI, in-session, Desktop Code tab) | `aantars` marketplace | Only after you turn on auto-update for the marketplace; otherwise run the update commands |
| Codex | `aantars` marketplace | Yes, at startup |
| Everyone else | skills.sh | No. Run `npx skills@latest update` |

Never promise "instant". Put any one-time opt-in beside its install command.

## Claude Code (CLI)

<canonical-block name="claude-code">

```bash
claude plugin marketplace add bradautomates/claude-video
claude plugin marketplace add aantars/skills
claude plugin install aantars-skills@aantars
```

The plugin declares `watch@claude-video` as a dependency, so the install also brings in `watch`. Adding the `claude-video` marketplace first is what makes that possible; skip step 2.

</canonical-block>

Why this shape: `plugin.json` lists `"dependencies": ["watch@claude-video"]` and `marketplace.json` allows it with `"allowCrossMarketplaceDependenciesOn": ["claude-video"]`. Claude Code does not register a dependency's marketplace on its own, so the `claude-video` marketplace must be added before the install. See https://code.claude.com/docs/en/plugins/dependencies.md.

## Claude Code (in a session)

<canonical-block name="claude-code-in-session">

```text
/plugin marketplace add bradautomates/claude-video
/plugin marketplace add aantars/skills
/plugin install aantars-skills@aantars
```

Then run `/reload-plugins` or start a new session. `watch` comes along as a dependency; skip step 2.

</canonical-block>

## Claude Desktop (Code tab)

<canonical-block name="claude-desktop">

1. Open **Customize**, select **Plugins**, then **Add** > **Add marketplace**.
2. Add `bradautomates/claude-video`, then add `aantars/skills`.
3. Find **aantars-skills** in the list and install it. `watch` should be installed with it; if it is not listed as installed, install **watch** too.
4. Use it from a **Code** session (not Chat or Cowork).

</canonical-block>

## Codex

<canonical-block name="codex">

```bash
codex plugin marketplace add aantars/skills
codex plugin add aantars-skills@aantars
```

Start a new Codex session afterwards.

</canonical-block>

## Every other agent, or editable files (skills.sh)

<canonical-block name="skills-sh-one-skill">

```bash
npx skills@latest add aantars/skills --skill video-to-html
npx skills@latest add aantars/skills --skill confluence-read
```

Run only the lines for the skills you want. Pick your agent when prompted (or pass `-a <agent>`). To update, run `npx skills@latest update`.

</canonical-block>

`skills@latest` is the pinned spelling everywhere.

## Updating and uninstalling

<canonical-block name="update-uninstall">

| Route | Update | Uninstall |
| --- | --- | --- |
| Claude Code | `claude plugin marketplace update aantars`, then `claude plugin update aantars-skills@aantars`. Or turn on auto-update for the `aantars` marketplace in `/plugin` > **Marketplaces**. | `claude plugin uninstall aantars-skills@aantars`, then `claude plugin marketplace remove aantars` |
| Claude Desktop | **Customize** > **Plugins**, open **aantars-skills** and update it | Same place, uninstall it |
| Codex | Updates itself at startup | Remove **aantars-skills** from the `/plugins` browser |
| skills.sh | `npx skills@latest update` | `npx skills@latest remove <skill-name>`, for example `video-to-html` |

`watch` updates and uninstalls the same way, with `watch@claude-video` and the `claude-video` marketplace.

</canonical-block>

## The two routes are exclusive

The plugin is a managed, read-only bundle you subscribe to. skills.sh writes files you own and edit. Installing both leaves the user with every skill twice: always say "pick one".

## Hard dependency: `watch`

`video-to-html` cannot run without the `watch` skill from [bradautomates/claude-video](https://github.com/bradautomates/claude-video). Every install story carries this block right after the skill install, as a required step, never as a footnote.

<canonical-block name="watch-dependency">

Claude Code (CLI):

```bash
claude plugin marketplace add bradautomates/claude-video
claude plugin install watch@claude-video
```

Claude Code (in a session):

```text
/plugin marketplace add bradautomates/claude-video
/plugin install watch@claude-video
```

Claude Desktop (Code tab): **Customize** > **Plugins** > **Add** > **Add marketplace**, enter `bradautomates/claude-video`, then install **watch**.

Codex:

```bash
codex plugin marketplace add bradautomates/claude-video
codex plugin add watch@claude-video
```

Any other agent:

```bash
npx skills@latest add bradautomates/claude-video -g --skill watch
```

`watch` needs Python 3.10+, ffmpeg and yt-dlp; its first-run setup checks them and helps you install what is missing. Videos without captions also need a transcription fallback: a Groq or OpenAI API key, or local WhisperX. `watch` does not work in Claude chat or Cowork, only in Claude Code, Codex and other local agent hosts.

`video-to-html` checks for `watch` before it starts and offers to install it if it is missing.

</canonical-block>

## First run

<canonical-block name="first-run">

Run `/watch` once on any short video, or just ask for `video-to-html`: it runs `watch`'s first-run setup for you. If you plan to convert videos without captions, have a Groq API key ready when the setup asks for a transcription fallback (or pick local WhisperX).

</canonical-block>
