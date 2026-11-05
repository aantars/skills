# Model-invoked vs user-invoked

Every `SKILL.md` is one of two kinds, split by who can reach it:

- **User-invoked**: reachable only by the human typing its name. Set `disable-model-invocation: true` in the frontmatter (Claude Code) and `policy.allow_implicit_invocation: false` in `agents/openai.yaml` (Codex). The `description` is human-facing: a one-line summary for someone browsing slash commands, with no trigger lists.
- **Model-invoked**: reachable by the model or the user. This is the default: omit `disable-model-invocation` and the `policy` block. The `description` is model-facing and keeps rich trigger phrasing ("Use when the user wants ..., mentions ..., asks for ...") so auto-invocation fires. The test: could the model usefully reach for this on its own?

Every skill carries `agents/openai.yaml` beside its `SKILL.md`, with `interface.display_name` and `interface.short_description` for the Codex skill picker. Keep it in sync with the frontmatter: a skill is user-invoked in both harnesses or neither.

The READMEs and promoted bucket `README.md`s group entries into **User-invoked** and **Model-invoked**.

## Dependencies between skills

When a skill needs another skill, say so as an explicit instruction to **call the Skill tool** with the named skill (`Call the Skill tool with "watch"`), not as a `../other-skill/FILE.md` reference or a bare `/name` left for the model to interpret. One skill per call. A user-invoked skill can never be reached this way; tell the user to run it instead.

A dependency on a skill from another repo is a **hard dependency**: follow the three-place rule in [AGENTS.md](../AGENTS.md).
