---
name: wechat-article-reading
description: Read full text content from WeChat/Weixin public account articles (mp.weixin.qq.com)
---

# WeChat/Weixin Article Reading

Read full text content from WeChat public account articles (mp.weixin.qq.com).

## Problem
`browser_snapshot` truncates content at ~8000 characters, making it impossible to get full articles through normal navigation.

## Solution
Use `browser_console` with JavaScript to extract complete text:

```javascript
document.body.innerText.substring(0, 8000)
```

Increase offset as needed for longer articles:
```javascript
document.body.innerText.substring(8000, 16000)
document.body.innerText.substring(16000, 24000)
```

## Workflow
1. `browser_navigate` to the mp.weixin.qq.com URL
2. `browser_snapshot` to see structure and identify content
3. If content is truncated, use `browser_console` with innerText extraction
4. `browser_scroll` + console extraction for multi-part content

## Notes
- WeChat articles often 10,000+ characters
- This approach bypasses the snapshot truncation limit
- Works for most public account article pages
