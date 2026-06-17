---
name: japanese-language-assistance
description: "Translate and analyze Japanese text — grammar breakdowns, vocabulary tables, particle summaries for N3-N2 learners."
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Japanese, Grammar, Translation, Language-Learning]
---

# Japanese Language Assistance

Translate Japanese sentences and provide detailed grammar analysis. Target audience: intermediate learner (N3-N2 level). User is Omi — a Chinese native speaker learning Japanese at N3-N2 level.

## When to use

- User posts a Japanese sentence and asks for translation
- User asks "解释语法" (explain grammar), "翻译", or "语法解析"
- User asks about specific particles, verb forms, or sentence patterns
- User asks how to say something in Japanese (中译日）
- User asks about reading (読み) or meaning of a specific word/form
- User asks to explain at a specific JLPT level (e.g., "用N3语法")
- User attaches a screenshot of Japanese textbook pages or learning material and asks "解释图中语法"
- Any Japanese text that needs breakdown beyond a simple translation

## Response format

Follow this structure for every grammar explanation:

### 1. 翻译 (Translation)
Natural Chinese translation first, so the user gets the meaning immediately.

For sentences from songs/poems/literature, note the source if known.

### 1b. 逐词解析 (Vocabulary) — OPTIONAL
When the sentence contains vocabulary likely unfamiliar to the user (N3-N2 or above), add a table before the grammar breakdown:

| 词汇 | 读音 | 含义 |
|------|------|------|
| 単身赴任 | たんしんふにん | 单身赴任 |
| … | … | … |

Skip this step for sentences made of basic N5-N4 vocabulary.

### 2. 逐层拆解 (Step-by-step Decomposition) — REQUIRED
This is the most distinctive and valued format section. Display the sentence as a left-to-right chain of constituents using arrows (→), showing the layered nesting. Two common variants:

**Arrow-chain format** — for verb conjugation chains or sequential attachment:
```
[花] を → [彫刻] され → て → いく
```

**Indented-annotation format** — for detailed breakdown with annotations:
```
銀行員                     → 名词"银行员工"
  ↓
という                    → "叫做……的"
  ↓
の                        → 形式名词（名词化）
  ↓
も                        → "也/连"
  ↓
体力がいる                → "需要体力"
```

For verb transformations, show the full morphological progression:
```
彫る（ほる）              → 原形（五段）
  ↓
彫られる                  → 受身（被动态）
  ↓
彫られて                  → て形
  ↓
彫られていく              → 补助动词「いく」持续相
```

This format helps the user see exactly how each piece attaches and transforms.

### 3. 结构树 (Structure Tree) — OPTIONAL but recommended
A tree/indented diagram showing hierarchical attachment, with vertical lines connecting modifiers to their heads:

```
[銀行員] という の も  [体力] が   [いる]  ん です ね
   │       │    │  │     │     │      │     │   │   │
   │       │    │  │     │     │      │     │   │   └─ 感叹
   │       │    │  │     │     │      │     │   └── 丁寧体
   │       │    │  │     │     │      │     └── 说明の
   │       │    │  │     │     │      └── 动词"需要"
   │       │    │  │     │     └── 主格助词
   │       │    │  │     └── 名词"体力"
   │       │    │  └── "也/连"
   │       │    └── 形式名词
   │       └── "叫做……的"
   └── 名词"银行员工"
```

### 4. 逐项语法 (Grammar Points)
Number each grammar point. For each point, use a table or structured block:

| 分解 | 作用 |
|------|------|
| component | role/meaning |

Cover:
- Particles (は、が、を、に、で、へ、と、から、まで、より…)
- Verb conjugations and their functions
- 形式名詞 (こと、の、まま、場合、ため…)
- Fixed patterns (〜とは〜ことです, 〜なければならない, あまり〜ない…)
- Compound/complex structures
- Adjectives modifying verbs or nouns

Provide similar examples (类似例子) for key patterns.

**N-level matching**: When the user says "用N3语法" (or any level), explicitly note the JLPT level of key grammar points in a column or footnote. If the user's version used N4 (〜ばいい), offer an N3 alternative (〜ようにしよう, 〜ことにする) with explanation of the nuance difference.

### 5. 对比说明 (Comparison) — OPTIONAL
When the user asks about a specific grammar point or when multiple similar patterns appear in one sentence (e.g., 五段verb使役 vs 一段verb使役, ～そうだ伝聞 vs ～そうだ様態), add a comparison table:

| 语法/形式 | 层级 | 含义 | 例 |
|-----------|------|------|-----|
| 行か**せる** | N4 | 五段使役 | 行く→行かせる |
| 覚え**させる** | N4 | 一段使役 | 覚える→覚えさせる |

Also useful when the user asks "A和B有什么区别" or when the sentence contains a form the user might confuse with a similar-looking one.

### 6. 助词总结 (Particle Summary) — OPTIONAL for short sentences
A compact table recapping every particle used in the sentence:

| 位置 | 助词 | 作用 |
|------|------|------|
| noun | が | subject marker |
| noun | を | object marker |
| … | … | … |

## Special query patterns

### 日语口语话题推荐 / conversation-topic coaching

When Omi asks for a Japanese speaking-class topic, especially for a 1-hour lesson around N4 level:

- Prefer ordinary daily-life topics unless he explicitly asks for work, investing, AI, medical, or other specialized subjects.
- Do not mine Omi's memory/history to propose topics from previous chats unless he asks for a personalized topic. Treat "日常生活中的话题" as a request for neutral everyday themes.
- Avoid deliberately suggesting illness, hospital, medical treatment, or health-abnormality topics for casual conversation practice unless Omi asks directly.
- Good N4-friendly topic classes: weekend routine, meals/cooking, shopping, weather and seasons, commute/transport, sleep and morning routine, housework, hobbies, movies/music, cafes/restaurants, travel memories, favorite places, smartphone habits, pets/animals, festivals/holidays.
- For each recommended topic, provide: why it fits, a 5-part conversation outline, teacher questions to ask, and N4 sentence patterns such as 〜たり〜たりします, 〜ことが多いです, 〜より〜ほうが好きです, 〜つもりです, 〜と思います.

### "这个词怎么读？是什么意思？" (reading + meaning)
When the user asks for the reading and meaning of a specific word form (e.g., 「彫られて」):

1. Give the reading first (ふりがな + romaji)
2. Break down the morphological chain step by step:
   - 原形 → 变形1 → 变形2 → 最终形
   - Explain each transformation rule
3. Show the complete conjugation table for the relevant form
4. Explain the meaning in context

### "用N3/N4语法版" (grammar level upgrade)
When the user asks for a version using a specific JLPT level:

1. Provide the original sentence
2. Explain what grammar point is being replaced and why
3. Show the level upgrade mapping table
4. Explain the nuance difference between the original and the upgraded version

### "A和B有什么区别" (comparison of similar forms)
For grammar comparison questions:

1. Present each form with its formation rule, meaning, and JLPT level
2. Use a comparison table
3. Give example pairs showing the contrast
4. Include a "语感差异" (nuance difference) column

## Textbook / screenshot image handling

When the user attaches an image of a Japanese textbook page or learning material (screenshot, photo):

1. **Load `read-image` skill** first
2. **Extract text** with mmx vision describe:
   ```bash
   mmx vision describe --image <path> --prompt "Extract ALL Japanese text from this image exactly as written. This is a Japanese textbook/learning material page. Output every Japanese sentence and note you see." --quiet
   ```
3. **Identify the grammar topic** (the title/header of the page, e.g. "助数詞＋する", "～通り")
4. **Present the response as**:
   - 完整文本 (all extracted text, including header, notes, example sentences, illustration text)
   - 语法核心 (core grammar concept explanation)
   - For each example sentence, apply the standard 翻译 → 逐层拆解 → 结构树 → 逐项语法 → 助词总结 breakdown
   - 总结 (summary comparison table if multiple usages are contrasted)

## Style rules

- Default: use **Chinese for all explanations** (user's native language). If user asks in English, match their language initially but offer to switch to Chinese.
- For Japanese speaking-class topic suggestions, prefer neutral daily-life topics (weekends, food, shopping, movies, travel, seasons, hobbies, housework, neighborhood) and do **not** deliberately mine the user's recent chat history or personal situations unless the user explicitly asks for a personalized topic.
- Do not proactively suggest illness, hospital, medical checks, or health-abnormality topics for casual Japanese conversation practice. Only discuss those if the user directly asks.
- Use Japanese terms for grammar concepts (連体形, 形式名詞, 使役, 受身, etc.) — the user is an intermediate learner who knows these terms
- Provide furigana (读音) in parentheses for vocabulary items on first mention
- Keep tables compact — avoid redundant columns
- Don't over-explain basic N5-N4 concepts; focus on N3-N2 patterns and nuances
- When a particle has multiple possible interpretations (e.g., で as 手段 vs 原因), note the ambiguity and give the most natural reading
- For sentence-long explanations (full context paragraph), include a 句子结构 overview showing how clauses connect (对比/因果/并列/etc.)
- When explaining 伝聞 (〜そうだ), always note that it comes after plain form (普通形)

## Pitfalls

- Don't just give a translation — the user specifically wants grammar analysis
- Don't skip the 逐层拆解 diagram — it's the format the user explicitly requested and values most
- Don't use English grammar terminology (no "gerund", "participle", "subjunctive") — use Japanese grammatical terms the user is familiar with
- For 〜なければならない, always break it down step by step (原形 → ない形 → 假定形 → なる否定) rather than just saying "must"
- Don't invent 解读 for song lyrics — note the literary/poetic nature and offer interpretations as possibilities
- When the user asks "用中文解释", switch fully to Chinese (not mixed English/Chinese) — this was a user correction
- When answering about ChatGPT Plus or other non-Japanese topics that arise mid-conversation, treat them as diverter questions, answer concisely, and don't get confused about the topic