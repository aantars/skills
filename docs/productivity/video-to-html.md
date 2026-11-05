## What it does

`video-to-html` turns a video into one HTML page you can read instead of watching. Give it a link or a file on your computer and you get a single, self-contained file: responsive, with light and dark themes, a working table of contents, screenshots embedded in the page and timestamps that jump back to the source. You can open it offline, email it or drop it in a shared folder.

It works **evidence first**: every sentence comes from the transcript and every image from a frame the agent actually looked at. It does not fill gaps from general knowledge or describe what a video "probably" shows. When something is unclear in the video, the page says so or leaves it out.

## When to reach for it

Type `/video-to-html`, or the agent reaches for it automatically when you ask to convert, document, summarise or write up a video, make a guide from a recording, or pull the key points out of a talk, webinar, demo or meeting.

It writes one of three kinds of page:

| You want | Pick | What you get |
| --- | --- | --- |
| To reproduce what the video shows | **Tutorial** | Numbered steps, one action each, with exact values, menu paths and commands, a screenshot per step that changes the screen, and common pitfalls |
| Only what is worth knowing | **Highlights** | The most useful or surprising moments, ranked by value rather than by time, often with a quote |
| A record of everything covered | **Full summary** | Every topic in video order, each with its main idea, supporting points and conclusions |

Leave it on **Auto** and it picks Tutorial for how-to videos and Full summary for the rest, and tells you which one it chose.

## Prerequisites

- The **`watch`** skill from [bradautomates/claude-video](https://github.com/bradautomates/claude-video). It downloads the video, pulls the transcript and extracts frames. `video-to-html` checks for it first and offers to install it if it is missing; the commands are in the [README](https://github.com/aantars/skills/blob/main/README.md#2-install-the-watch-dependency-required).
- **Python 3.10+**, **ffmpeg** and **yt-dlp** on your machine. `watch`'s first-run setup checks them and helps you install what is missing.
- For videos **without captions**: a transcription fallback in `watch` (a Groq or OpenAI API key, or local WhisperX). Without one, the page is built from the visuals only and comes out thinner.
- An agent that runs on your computer: Claude Code (terminal, VS Code or the Desktop **Code** tab), Codex, or another local agent host.

It writes everything into a new folder in your current directory, named `YYYY-MM-DD_<slug>/`.

## How a run goes

**Default or customise.** The first question is whether to accept the defaults (type Auto, your language, standard detail, whole video) or customise. Customising lets you choose the type, the page language, the detail level (Concise, Standard or Detailed) and extras such as a glossary, clickable timestamps, a time range only, or larger images for videos full of code or small text.

**Scene estimation.** Before looking at any frames, it measures how visually busy the video is and shows you a short table:

| Value | What it tells you |
| --- | --- |
| Duration | Length of the part being analysed |
| Scene changes (sensitive / standard / major) | How often the picture changes: small changes such as a new line of code, or only big ones such as a new slide |
| Timeline | A sparkline of changes per minute; the tall bars are where most of the visual action is |
| Static video | Whether it is mostly the same picture (a talking head, one slide), in which case the transcript carries the content |
| Budgets (light / balanced / thorough) | How many frames will be analysed, with an approximate image-token cost |

It recommends a budget (usually balanced) and waits for you to confirm it, along with the scope.

**Anonymisation.** It asks whether anything should be blurred: a fixed area such as a webcam overlay or an address bar (you see a preview first), sensitive data it detects automatically such as emails, names, tokens or faces (you approve the list before anything is blurred), both, or nothing.

**The work itself.** The video is split into a few segments, and each one is handled by a [subagent](https://www.aihero.dev/ai-coding-dictionary/subagent) with a fresh [context window](https://www.aihero.dev/ai-coding-dictionary/context-window), so frames from one part do not crowd out the rest. The pieces are then joined into one page, checked for broken links and missing images, and built.

**Keep or delete the video, and clean up.** For online videos, you choose at the start whether to keep the downloaded file next to the page or delete it. Either way, all working files (frames, transcript, drafts) are deleted at the end. A local video you pointed it at is never moved, changed or deleted.

## Common questions

**How much does a run cost?**
Most of the cost is images. Each analysed frame at the default width is roughly 800 image tokens, so a balanced run on a busy screen recording can reach tens of thousands of tokens, while a talking-head video needs only a handful of frames. The scene estimation step shows the estimate before any frame is analysed, and you can drop to the light budget or a shorter time range.

**Does it work in Claude chat or Cowork?**
No. `watch` needs to download and process the video with tools on your machine, so it only works in Claude Code, Codex and other agents that run locally.

**Can it handle private or internal videos?**
For a link, it can only download what yt-dlp can reach from your machine. For a private recording, download it yourself and give the agent the file path. Video and frames are processed locally; the one exception is a cloud transcription fallback (Groq or OpenAI), which sends the audio to that provider. Use local WhisperX if that matters.

**Can the page be in a different language from the video?**
Yes. The page language is a separate choice: your language, the video's, English or any other. Headings, labels and the table of contents follow it.

**What about long videos?**
They work, but cost grows with length. The video is split into segments of a few minutes each and processed in parallel, so a one-hour talk is fine. For a long video where only part matters, choose **Only a time range** to skip the rest.

## It's working if

- Every screenshot shows something the text refers to, and its caption tells you what to look at.
- Following a Tutorial page step by step reproduces what the video shows, without watching it.
- The timestamps jump to the right moment in the source.
- The page reads well in light mode, dark mode and on a phone, with no sideways scrolling.
- The output folder holds only the HTML (and the video, if you chose to keep it): no leftover frames or drafts.

## Where it fits

A standalone tool you reach for whenever a video needs to become something people can read, search and share. It builds on [watch](https://github.com/bradautomates/claude-video), which answers questions about a video in the conversation; `video-to-html` turns the same evidence into a lasting document.
