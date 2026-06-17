# Image Prompt Guidance

## What Works Well with mmx image generate

- **Mood and atmosphere**: "warm festive celebration", "cyberpunk neon city at night", "serene Japanese garden in autumn"
- **Color palettes**: "blue and gold color scheme", "pastel pink and mint green", "warm sunset tones"
- **Style references**: "flat design illustration", "watercolor style", "3D render with soft shadows", "minimalist UI mockup"
- **Subject + setting**: "a corgi wearing a spacesuit floating in space", "modern office interior with large windows"
- **Composition**: "centered composition", "birds-eye view", "slight low angle", "close-up portrait"

## What Doesn't Work

- **Specific symbols or shapes**: `{{>}}`, `<?>`, `()`, specific logo marks — AI cannot reliably reproduce these
- **Exact text rendering**: any specific text/logo will be approximated, often incorrectly spelled
- **Fine details**: small text, intricate patterns, precise layouts — will be distorted

## Brand/Logo Generation Strategy

When generating brand-related imagery:

1. **DO describe visual properties**: "flowing ribbon logo with blue-purple-cyan gradient", "circular icon with three intersecting dots"
2. **DO NOT use symbolic notation**: "the {{>}} symbol", "the Copilot curved arrow"
3. **Describe the FEELING**: "modern tech company logo with friendly rounded edges", "luxury brand with gold accents"

## Examples

### Good Prompt
> Microsoft Copilot logo with flowing ribbon shape in gradient blue to purple through cyan, the ribbon creates an infinity loop, surrounded by confetti in red blue yellow, text "Celebrating" in orange, clean modern flat illustration style

### Bad Prompt
> Microsoft Copilot {{>}} logo with fireworks

### Good Prompt (abstract art)
> Abstract flowing ribbons in gradient colors from blue to purple to orange creating an S-curve, modern digital art style, clean background

### Bad Prompt
> Draw the symbol {{>}} exactly as shown

## Sensitive Content

Avoid vivid descriptions of:
- Weapons, military equipment
- Violence or blood
- Explicit/adult content
- Real political figures

These trigger `new_sensitive` errors (exit code 10).