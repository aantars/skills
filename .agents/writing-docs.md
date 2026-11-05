# Writing docs pages

Every skill in a promoted bucket (`productivity/`, `engineering/`) has a human-facing docs page in two languages: `docs/<bucket>/<skill-name>.md` (English) and `docs/<bucket>/<skill-name>.es.md` (Spanish, Spain). The docs tree mirrors the promoted bucket folders. The page is not the skill and not a copy of `SKILL.md`: its job is to orient one reader around one skill so they know what it does, when to reach for it and what to expect.

Create or re-sync both pages whenever a promoted skill is added, renamed, or changes behaviour. A rename moves both files. A skill that leaves the promoted buckets loses its pages; one removed outright keeps them, opened with a `> **Archived.** ...` notice naming the version it was removed in and any replacement.

**Every link is absolute**: `https://github.com/aantars/skills/blob/main/...` for repo files, full URLs for everything else. Pages may be read outside the repo, where relative links break.

**No install commands.** Install wording lives in the READMEs, copied from [install-block.md](./install-block.md). A page that repeats it drifts. Mention a dependency by name and link it; point to the README for how to install.

There is no H1.

## Page template

Keep this order. `What it does`, `When to reach for it` and `Where it fits` are always present; the others only when they have real content.

<page-template>

## What it does

One or two plain paragraphs. Lead with the skill's one-sentence job, then state its **defining constraint** as a plain sentence (never a labelled aside like "The key thing:"). This line is the most valuable on the page.

## When to reach for it

- **Invocation mode.** User-invoked: "You invoke this by typing `/<name>`; the agent won't reach for it on its own." Model-invoked: "Type `/<name>`, or the agent reaches for it automatically when a task fits."
- **Trigger boundary.** "Reach for this when ...". Where the skill offers a choice (output types, modes), show it as a table.

## Prerequisites

Only when the skill needs something in place: a dependency, a tool, a folder it writes into. Omit the heading otherwise.

## <free-form middle>

One to three short sections, in the skill's own vocabulary, that make it click: the flow it runs, the choices it asks for, what it leaves behind. Surface the skill's **leading idea** (for `video-to-html`: evidence first). Explain the why, not the runbook.

## Common questions

Real questions, sharpest first, each in bold with the answer below. Keep the count honest: three good questions beat six invented ones. Say the unflattering thing where it is true. Omit the heading when there is nothing worth answering.

## It's working if

A few bullets the reader can check without opening `SKILL.md`, in their own output or in the session in front of them.

## Where it fits

One or two sentences: the skill's role (standalone, chain step, setup) and the one or two neighbours that matter, linked absolutely.

</page-template>

## Conventions

- Branches go in a table or a list, never in a paragraph.
- Never name the author. State claims about the skill plainly.
- Keep the page short and low-load: no spare headings, no restated links.
- The Spanish page says the same as the English one, written as natural Spanish rather than a literal translation. Change both in the same change.
