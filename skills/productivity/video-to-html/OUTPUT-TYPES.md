# Output types and HTML components

## The three types

| Type | Reader's question | Chapter shape | Images |
| --- | --- | --- | --- |
| **Tutorial** | "How do I do this myself?" | Goal of the step, prerequisites, numbered `ol.steps` (one action per step, exact values, menu paths, commands in `pre code`), the expected result, common pitfalls as `callout warn` | One per step that changes the screen; show the result state |
| **Highlights** | "What is worth knowing?" | Only the most interesting, surprising or useful moments, ranked by value, not by time. Each: what was said or shown, why it matters, a quote when it lands | Only the frames that carry the point; often 1 per chapter |
| **Full summary** | "What was covered?" | Every topic, in video order. Per topic: the main idea in 1 to 2 sentences, supporting points, examples, any decision or conclusion | Diagrams, slides, demos; skip talking heads |

Detail levels scale length, not structure:

| Detail | Words per chapter | Images per chapter |
| --- | --- | --- |
| Concise | 80 to 180 | 0 to 1 |
| Standard | 180 to 450 | 1 to 3 |
| Detailed | 450 to 900 | 2 to 6 |

## Components

Fragments are plain HTML that `build_html.py` drops into the template. Use only these components so the styling holds; no inline styles, no scripts, no external resources.

```html
<section class="chapter" id="s03-configure-api-key">
  <h2>Configure the API key</h2>
  <p class="chapter-meta"><a class="ts" data-t="312">5:12</a></p>
  <p class="lead">One sentence on what this chapter gives the reader.</p>

  <h3 id="s03-where-to-find-it">Where to find it</h3>
  <p>Short paragraph.</p>

  <figure class="shot">
    <img src="C:/abs/path/to/frame.jpg" alt="Settings page with the API keys tab open">
    <figcaption>Open <strong>Settings → API keys</strong> and click <em>Create</em>. <a class="ts" data-t="331">5:31</a></figcaption>
  </figure>

  <div class="shots"><!-- 2 to 4 related screenshots side by side --> <figure class="shot">...</figure> <figure class="shot">...</figure></div>

  <ol class="steps">
    <li><strong>Create the key</strong><p>What to click and what to type.</p></li>
  </ol>

  <div class="callout tip"><p class="callout-title">Tip</p><p>...</p></div>
  <div class="callout note"><p class="callout-title">Note</p><p>...</p></div>
  <div class="callout warn"><p class="callout-title">Careful</p><p>...</p></div>

  <ul class="keypoints"><li>One takeaway per item.</li></ul>
  <blockquote class="quote"><p>Short, striking quote.</p><footer>Speaker, <a class="ts" data-t="402">6:42</a></footer></blockquote>
  <pre><code>npm install example</code></pre>
  <div class="table-wrap"><table><thead><tr><th>Option</th><th>Effect</th></tr></thead><tbody><tr><td>...</td><td>...</td></tr></tbody></table></div>
  <dl class="glossary"><dt>Term</dt><dd>Plain definition.</dd></dl>
</section>
```

Rules:

- **ids** are lowercase ASCII with hyphens, prefixed with the segment number (`s03-...`), so fragments written in parallel never clash. The `<section>` id is the TOC anchor; every `<h3>` that should appear in the TOC needs an id too.
- **Timestamps**: `<a class="ts" data-t="SECONDS">m:ss</a>` with whole seconds in the source video. The build turns them into links to that moment, or plain chips for local files.
- **Images**: `src` is the absolute path of the frame file; the build embeds it. `alt` says what the image shows; the caption says what to look at.
- Callout titles are written in the page language.
- Translate everything into the page language, including UI text visible in screenshots when you quote it (keep the original label in brackets when the reader must find it on screen: *Ajustes* (*Settings*)).
