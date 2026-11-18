## What it does

`jira-read-attachments` reads a Jira issue the way a person does: the fields, description and comments, plus the screenshots, logs and attached files (PDFs, XML, patches) that explain it. Everything goes through a small bundled script that calls Jira's REST API with your browser session cookie, so it works where an MCP server cannot download attachments.

The session cookie never goes through the chat. You store it once, in your own terminal, with the bundled script. It is kept (encrypted with your Windows account on Windows) and the agent only ever sees whether it is valid, expired or rejected.

## When to reach for it

Type `/jira-read-attachments`, or the agent reaches for it automatically when you share a Jira issue link or key and want its attachments or images read, mention a Jira session cookie, or an attachment download from the Jira MCP fails. For a quick text-only summary of a ticket, use a plain Jira reader instead.

Each time, it asks what to read besides the text:

| You pick | It reads |
| --- | --- |
| **Images** | Screenshots, each matched to the description or comment that mentions it |
| **Attachments** | PDFs, XML, logs, patches, SQL and other attached files |
| **Both** | Everything above |
| **Text only** | Just the issue text; nothing is downloaded |

For an issue with many attachments, it then asks which ones matter for your question and fetches only those.

## Prerequisites

- **Jira Server or Data Center.** Jira Cloud serves attachments from another host that a session cookie does not open.
- **Python 3.10+.** The script uses the standard library only.
- An agent that runs on your computer: Claude Code (terminal, VS Code or the Desktop **Code** tab), Codex, or another local agent host.

## The cookie

The first time you ask for an issue, or whenever the stored cookie stops working, the agent tells you why and hands you one command to run in your own terminal. That command shows how to copy the cookie from your browser's developer tools (the full `Cookie` request header from the Network tab, or just `JSESSIONID`), asks for it hidden while you paste, asks for an optional expiry date, checks it against Jira and saves it in `~/.jira-read/cookies.json`.

| Cookie state | What happens |
| --- | --- |
| Valid | Nothing to say; it reads the issue |
| Expires within a day | One line with the date, then it reads |
| Expired, missing or rejected by Jira | It stops, tells you why and gives you the renewal command |

A Jira session usually ends on the server side (a timeout or signing out), so "rejected" is the state you will meet most. The script records it, so the next session already knows. The cookie is only ever sent to your Jira host.

## Common questions

**Why not just paste the cookie into the chat?**
Because it is a live session: anyone holding it is signed in as you. Pasted in the chat it stays in the conversation history. Typed into your own terminal, it goes straight into the encrypted store. If you paste it anyway, the agent will not use it and will suggest signing out of Jira to invalidate it.

**Can it change my issues?**
No. The script only reads.

**Where do the downloaded files go?**
To a temporary folder, deleted when the answer is done, unless you ask to keep them somewhere.

## It's working if

- You get answers about what is on an issue's screenshots and in its attached files, not just its text.
- You are asked for the cookie only when it is missing, expired or rejected, and never asked to paste it in the chat.
- No downloaded files are left behind unless you asked to keep them.

## Where it fits

A standalone reading tool for Jira issues. It complements a Jira MCP server such as [mcp-atlassian](https://github.com/sooperset/mcp-atlassian) for text, search and editing, and sits next to [confluence-read](https://github.com/aantars/skills/blob/main/skills/productivity/confluence-read/SKILL.md), which does the same for wiki pages.
