# Segment agent brief

Copy this brief into each subagent's prompt, with the placeholders filled in. Start each subagent with a **fresh context window**, never a fork of the main conversation.

---

You are writing one chapter group of an HTML page built from a video. Other agents write the other segments in parallel; the main agent assembles the page.

**Segment:** `{NN}`, working title "{TITLE_GUESS}", from `{START}` to `{END}`.
**Video:** `{VIDEO_PATH}`. **Transcript report:** `{TRANSCRIPT_PATH}` (read only the lines inside your range, plus a few seconds either side for context).
**Page:** type `{TYPE}`, language `{LANG}`, detail `{DETAIL}`. Structure and HTML components: `{SKILL_DIR}/OUTPUT-TYPES.md` (read it first).
**Flag sensitive data:** `{FLAG_SENSITIVE}`.
**Write to:** fragment `{SECTIONS_DIR}/{NN}_<slug>.html`; scratch dir `{SEG_DIR}`.

## Steps

1. Extract frames for your range only:

   ```bash
   python "{WATCH_PY}" "{VIDEO_PATH}" --engine local --detail balanced --start {START} --end {END} --max-frames {BUDGET} --resolution {RESOLUTION} --no-whisper --out-dir "{SEG_DIR}"
   ```

   For a dense screen recording where the text changes subtly, add `--no-dedup`. If the transcript points at a moment ("look here", "now click"), add `--timestamps` for it.
2. **View every frame listed in the report** with your image-reading tool, and read your transcript range. Note for each frame what it shows and whether it adds something the text cannot.
3. Decide your chapters: usually 1 to 3 `<section class="chapter">` for your segment, split where the topic changes. Ids start with `s{NN}-`.
4. Write the fragment following `OUTPUT-TYPES.md` for your type and detail level, in `{LANG}`. Choose images: the clearest frame of each state that matters; no near-duplicates; no frames that only show a face. Reference them by absolute path.
5. If `{FLAG_SENSITIVE}` is yes, look in the frames you used for emails, personal names, phone numbers, API keys, tokens, passwords, private URLs or ids, and faces of people who are not the presenter.

## Writing rules

- Write for someone who has not seen the video. Lead with the point, short paragraphs, plain words, explain jargon once.
- Only state what the transcript says or the frames show. If something is unclear, leave it out or say it is unclear.
- Do not open or close with filler ("In this section we will see..."). Do not repeat the intro or conclusions; the main agent writes those.
- Give exact values, menu paths and commands when the video shows them.

## Return

Reply with JSON only:

```json
{
  "fragment": "{SECTIONS_DIR}/{NN}_<slug>.html",
  "chapters": [{"id": "s{NN}-...", "title": "...", "start": "m:ss"}],
  "summary": "2 to 3 sentences on what this segment covers, for the intro and TL;DR",
  "takeaways": ["one-line takeaway", "..."],
  "images_used": ["absolute path", "..."],
  "sensitive": [{"image": "absolute path", "time": "m:ss", "what": "email address", "region_percent": "X,Y,W,H"}],
  "gaps": ["anything you could not read or hear"]
}
```
