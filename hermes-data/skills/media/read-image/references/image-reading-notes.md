# Image Reading — Known Working Patterns

## Always Use `mmx vision describe`

Do NOT use the built-in `vision_analyze` tool for local images — it fails on local filesystem paths.

```bash
export PATH="$HOME/.local/bin:$PATH"
mmx vision describe --image <path-or-url> --prompt "<question>" --quiet
```

---

## Tool Availability Check

```bash
export PATH="$HOME/.local/bin:$PATH"
mmx --version  # should return 1.0.x

API_KEY=$(grep MINIMAX_CN_API_KEY /Users/omi/.hermes/.env | cut -d= -f2)
mmx auth login --api-key "$API_KEY"
```
