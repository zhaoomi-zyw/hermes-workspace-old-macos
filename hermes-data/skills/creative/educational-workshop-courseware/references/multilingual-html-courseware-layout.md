# Multilingual HTML Courseware Layout Notes

Use this reference when editing student-facing HTML courseware that contains the same learning point in multiple languages.

## Pattern

For short course goals, cards, or key messages, prefer per-item vertical language stacking when the user asks for legibility:

1. English
2. German
3. Chinese

Each learning point should stay grouped as one card or block, with its language variants stacked inside that block. This is easier to read than a three-column layout when each card already belongs to a grid.

## CSS approach

- Scope the change to the affected section instead of changing all multilingual blocks globally.
- Add a section-specific or block-specific class, e.g. `workshop-goals` on the section and `goal-tri` on the language stack.
- Keep the existing global multilingual class for other pages/sections if they still need side-by-side layout.
- Example:

```html
<section class="section workshop-goals">
  <div class="card">
    <h3>Understand the shift</h3>
    <div class="tri goal-tri">
      <div class="lang en">A chatbot answers questions. An agent completes tasks.</div>
      <div class="lang de">Ein Chatbot beantwortet Fragen. Ein Agent erledigt Aufgaben.</div>
      <div class="lang zh">聊天机器人回答问题；Agent 完成任务。</div>
    </div>
  </div>
</section>
```

```css
.goal-tri{
  display:flex;
  flex-direction:column;
  gap:10px;
}
.goal-tri .lang{
  width:100%;
  font-size:15px;
  line-height:1.5;
  font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}
.goal-tri .lang.zh{font-size:15px;}
```

## Verification

After editing:

- Open the HTML page in a browser.
- Use computed styles to confirm the scoped stack uses `display:flex` and `flex-direction:column`.
- Confirm English, German, and Chinese use the requested consistent font and size in that section.
- Check the browser console for errors.

## Pitfall

Do not satisfy “stack the languages and keep fonts consistent” by changing the global `.tri` or `.lang.zh` rules unless the user wants every multilingual block across the package to change. Scope the CSS so existing pages keep their intended layouts.
