## What it does

`confluence-read` reads a Confluence page the way a person does: the text, plus the screenshots, diagrams and attached files (PDFs, XML, patches, SQL) that explain it. The text comes through your Confluence MCP server; images and attachments come through a small bundled script, because on a wiki protected by a 2FA plugin those downloads need a browser cookie that MCP servers do not have.

The 2FA cookie never goes through the chat. You store it once, in your own terminal, with the bundled script. It is kept with its expiry date (encrypted with your Windows account on Windows), and the agent only ever sees whether it is valid, about to expire, expired or rejected.

## When to reach for it

Type `/confluence-read`, or the agent reaches for it automatically when you share a Confluence page link, ask it to read, review or summarise a wiki page, or want to know what a page's screenshots or attached files show.

Each time, it asks what to read besides the text:

| You pick | It reads |
| --- | --- |
| **Images** | Screenshots and diagrams, each matched to the section of the page it illustrates |
| **Attachments** | PDFs, XML, patches, SQL and other files attached to the page |
| **Both** | Everything above |
| **Text only** | Just the text; the cookie is not checked or mentioned |

For a page with many attachments, it then asks which ones matter for your question and fetches only those.

## Prerequisites

- **Confluence Server or Data Center.** Confluence Cloud does not use this 2FA cookie.
- **A Confluence MCP server** for the text, such as [mcp-atlassian](https://github.com/sooperset/mcp-atlassian). Without one, the script exports the text itself, as Markdown.
- **A Personal Access Token** (Confluence: Profile > Personal Access Tokens), saved in `~/.confluence_token` or in the `CONFLUENCE_TOKEN` environment variable.
- **Python 3.10+.** The script uses the standard library only.
- An agent that runs on your computer: Claude Code (terminal, VS Code or the Desktop **Code** tab), Codex, or another local agent host.

## The cookie and its expiry date

The first time you ask for images or attachments, or whenever the stored cookie stops working, the agent tells you why and hands you one command to run in your own terminal. That command shows where to find `Confluence_2FASessionVerified` in your browser's developer tools, asks for its value (hidden while you paste), asks for its expiry date (the **Expires / Max-Age** column), tests it against the page and saves both in `~/.confluence-read/cookies.json`.

From then on, before downloading anything, the agent checks the stored date. You hear about the cookie only when it matters:

| Cookie state | What happens |
| --- | --- |
| Valid | Nothing to say; it downloads |
| Expires within a day | One line with the date, then it downloads |
| Expired, missing or rejected by the wiki | It stops, tells you why and gives you the renewal command |

"Rejected" covers a cookie the wiki refuses before its date, for example after you sign out. The script records that too, so the next session already knows.

## Common questions

**Why not just paste the cookie into the chat?**
Because it is a live, already-verified session: anyone with it is signed in as you, past the 2FA. Pasted in the chat it stays in the conversation history. Typed into your own terminal, it goes straight into the encrypted store.

**How often do I have to renew it?**
As often as your wiki makes you sign in again with 2FA; the expiry date in the developer tools tells you. Renewing takes about a minute.

**Where do the downloaded files go?**
To a temporary folder, deleted when the answer is done, unless you ask to keep them somewhere.

**Does it work with any Confluence?**
It is built for Server and Data Center with a 2FA plugin that sets `Confluence_2FASessionVerified`. Without 2FA it still works: the downloads simply succeed with the token alone.

## It's working if

- You get answers about what is on a page's screenshots, not just its text.
- You are asked for the cookie only when it is missing, expired or rejected, and never asked to paste it in the chat.
- After a renewal, the next session downloads images without asking anything.
- No downloaded files are left behind unless you asked to keep them.

## Where it fits

A standalone reading tool for wiki pages. It complements a Confluence MCP server such as [mcp-atlassian](https://github.com/sooperset/mcp-atlassian): the server covers text, search and editing; `confluence-read` adds the images and attachments the server cannot download.
