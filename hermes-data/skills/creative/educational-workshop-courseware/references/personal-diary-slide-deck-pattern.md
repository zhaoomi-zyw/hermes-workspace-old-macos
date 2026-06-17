# Personal Diary Slide-Deck Pattern for Student Internships

Use this reference when the user wants to create a **personal reflection diary page** for a student/intern, presented as a **scroll-snap PPT-style slide deck**, with bilingual content (English main + German supportive).

## When to use this pattern

- The user wants a personal, reflective page (not a workshop deck or courseware).
- The content is based on the student's own experiences (internship, travel, exchange program).
- The output should feel like a short visual presentation, not a long-scroll article.
- The audience is international (English primary, German or other language secondary).

## Workflow

### Phase 1: Guided Q&A collection

Before generating anything, ask the user to describe the student's experience. Structure the questions to cover:

1. **First impression** — What city? What struck them immediately (airport, payments, food, pace)?
2. **What they did** — Company/team type, specific projects, tools used.
3. **What they learned** — Skills, work habits, team observations.
4. **Cultural observations** — Differences in daily life, communication, transport, food, digital life.
5. **AI tools they tried** — Which tools, what they evaluated, key findings.
6. **Biggest surprise** — Anything unexpected.
7. **Next questions** — What they still want to learn or explore.

Collect answers progressively (one or a few at a time). The user may answer partially; work with what you get and generate plausible content for unfilled sections based on the student's context.

### Phase 2: Slide deck structure

Generate a single self-contained HTML file with scroll-snap full-viewport slides:

```
Slide 0 — Hero (cover)
Slide 1 — First Impression   (cards + accent box)
Slide 2 — What I Learned     (cards + quote + accent box)
Slide 3 — Cultural Observations (2×2 card grid + accent box)
Slide 4 — AI Tools I Tried   (4× card grid + accent box)
Slide 5 — What I Want to Learn Next (checklist)
Slide 6 — Closing (thank you / footer)
```

### Component inventory

| Component | CSS pattern | Purpose |
|-----------|-------------|---------|
| **Hero** | Full-viewport dark gradient, centered text, label + title + subtitle + meta + scroll arrow | Cover slide |
| **Slide heading** | `.slide-number` (01/06) + `.slide-heading` (English) + `.slide-heading-de` (German italic) | Each content slide |
| **Card grid** | `.card-grid` (2-col or 3-col) with `.card` > `.card-label` + `.card-title` + `.card-text` | Grouped insights |
| **Accent box** | `.accent-box` (light blue-grey bg, 3px left border, rounded right) + `.de-note` inside | Key callout with German |
| **Quote block** | `.quote` centered, italic, curly-quote ::before/::after | Pacing / reflection break |
| **Checklist** | `ul.checklist` with `☐` ::before, each item has `.de-note` span | "What I want to learn next" |
| **Progress dots** | `.progress` fixed right rail, one dot per slide, IntersectionObserver active-highlight | Navigation aid |
| **Footer** | Dark background slide, centered thank-you + meta | Closing slide |

### Bilingual pattern

- English is the primary visible language (titles, body text, card content).
- German is supportive, in **two specific placements**:
  1. **Slide heading**: `.slide-heading-de` directly under the English slide title, italic gray.
  2. **Accent box**: `.de-note` line at the bottom of the `.accent-box`, italic gray, with German flag emoji prefix `🇩🇪`.
  3. **Checklist**: Each `<li>` has a `.de-note` span showing the German translation.
- Do NOT duplicate entire paragraphs in German. Keep translations concise (1-2 sentences max).

### CSS pattern for bilingual text

```css
.slide-heading-de {
  font-size: 0.82rem;
  font-weight: 400;
  color: #999;
  font-style: italic;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e0ddd6;
}

.accent-box .de-note {
  font-size: 0.8rem;
  color: #777;
  font-style: italic;
  margin-top: 0.4rem;
}

.checklist li .de-note {
  display: block;
  font-size: 0.78rem;
  color: #999;
  font-style: italic;
  margin-top: 0.15rem;
}
```

### Scroll-snap implementation

```css
html { scroll-snap-type: y proximity; }
.slide {
  min-height: 100vh;
  scroll-snap-align: start;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem 2rem;
}
```

### Progress dot navigation

```html
<nav class="progress">
  <a href="#slide-0" class="active"></a>
  <a href="#slide-1"></a>
  <!-- ... per slide ... -->
</nav>

<script>
const observer = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      document.querySelectorAll('.progress a').forEach(a => a.classList.remove('active'));
      const dot = document.querySelector(`.progress a[href="#${entry.target.id}"]`);
      if (dot) dot.classList.add('active');
    }
  });
}, { threshold: 0.5 });
document.querySelectorAll('.slide[id]').forEach(s => observer.observe(s));
</script>
```

Accessibility: dots are `<a>` elements with `aria-label`, not bare divs.

### Visual design rules

- **Color palette**: Dark navy/teal hero (#0f1f2b bg, #7ec8d8 accent), off-white body bg (#f5f4f0), dark headings (#0f1f2b), light gray sub-text (#999), blue accent (#2c7a8a for borders).
- **Typography**: Inter (professional, clean, modern).
- **Cards**: White bg, very subtle 1px border (#e6e3dc), rounded 10px. No heavy shadows.
- **No flashy elements**: No gradients in body, no heavy shadows, no decorative blobs/waves, no animation beyond the subtle hero arrow float and hover card shadow.

### Handling incomplete answers

When the user says "没了" (nothing more) for some questions:
- Use the information they *did* provide to infer plausible content for unfilled sections.
- For "What I Want to Learn Next," generate 4-5 realistic questions based on the student's context (e.g., AI regulation, language learning, longer stay, building their own tool).
- For "Cultural Observations," derive observations from what they mentioned (e.g., mobile payments → digital life card, e-scooters → transport card).
- Never fabricate personal claims (e.g., "I spoke fluent Chinese", "I visited Beijing"). Only use what the user actually stated.

## When to prefer this over courseware

| Use case | Preferred format |
|----------|-----------------|
| Workshop/lesson | `educational-workshop-courseware` skill (multi-page courseware) |
| Personal reflection diary | This pattern (single slide-deck HTML) |
| Company/career portfolio | Hybrid — slide deck structure but more formal tone |
| Internship report for school | This pattern, with more emphasis on learning outcomes |
