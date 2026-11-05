Skills are organized into bucket folders under `skills/`:

- `productivity/`: daily non-code workflow tools
- `engineering/`: daily code work (none yet; create the folder with the first one)
- `misc/`: kept around but rarely used, not promoted
- `in-progress/`: beta, public on purpose, not shipped in the plugin
- `deprecated/`: no longer used

Only create a bucket folder when its first skill arrives.

## Promoted skills

`productivity/` and `engineering/` are the **promoted** buckets. Every skill in them must have:

- an entry in the top-level `README.md` and `README.es.md`, with the skill name linked to its `SKILL.md`;
- an entry in `.claude-plugin/plugin.json`'s `skills` array (the plugin ships exactly the promoted set);
- an entry in its bucket's `README.md`, with a one-line description and the name linked to its `SKILL.md`;
- a docs page in both languages: `docs/<bucket>/<skill-name>.md` (English) and `docs/<bucket>/<skill-name>.es.md` (Spanish), following [.agents/writing-docs.md](./.agents/writing-docs.md).

Skills in `misc/`, `in-progress/` and `deprecated/` appear in none of these. When you add, rename, or change the behaviour of a promoted skill, create or re-sync all of the above in the same change.

The READMEs and the promoted bucket `README.md`s group entries into **User-invoked** and **Model-invoked**. Every skill is one or the other, and carries an `agents/openai.yaml` beside its `SKILL.md`. See [.agents/invocation.md](./.agents/invocation.md).

## Install wording and manifests

Install commands are copied verbatim from [.agents/install-block.md](./.agents/install-block.md). Change them there first, then propagate to both READMEs. Docs pages carry no install commands.

`.claude-plugin/marketplace.json` (marketplace `aantars`) is the repo's own marketplace, and lists one plugin, `aantars-skills`, defined in `.claude-plugin/plugin.json`. Bump `version` in `plugin.json` on every release, or plugin users get no update. Run `claude plugin validate . --strict` from the repo root after touching either manifest, and fix everything it reports.

## Hard dependencies

When a skill cannot work without another skill or tool, document it in three places, all in the same change:

1. the install section of `README.md` and `README.es.md`, as a required step;
2. a canonical block in `.agents/install-block.md`;
3. a preflight step at the top of the skill's `SKILL.md` that checks for the dependency and offers to install it.

`video-to-html` depends on `watch` from [bradautomates/claude-video](https://github.com/bradautomates/claude-video).

## Two languages

Every user-facing doc exists in English and Spanish (Spain) and is kept in sync: `README.md` / `README.es.md`, and every docs page `<name>.md` / `<name>.es.md`. A change to one is applied to the other in the same change. The Spanish version is written as natural Spanish, not a literal translation. Each pair links to its twin at the top (READMEs) or is linked from its README (docs pages). Agent-facing files (`SKILL.md` and its bundled files, `AGENTS.md`, `.agents/*`) stay in English only.

## Writing rules

No em-dashes anywhere in this repo (skills, docs, READMEs, code comments). Where a sentence reaches for one, rewrite it with a comma, colon, period, parentheses or a conjunction; never do a blind character substitution. Before finishing, search the repo for the em-dash character and remove any.

Write clear, plain, friendly prose. Lead with what the reader gets.

Every skill that dispatches a subagent says to start it with a fresh context window. Some harnesses fork the parent conversation by default, and a fork inherits the context the subagent was meant to escape.
