---
name: 163-music-lyrics
description: Fetch Chinese song lyrics quickly via NetEase Music 163 API
---
# 163 Music Lyrics Fetcher

## When to Use
Need to find lyrics for Chinese pop songs quickly and reliably.

## API Endpoints

**Search for song ID:**
```
GET https://music.163.com/api/search/get?type=1&s=SONG_NAME&limit=5
```
Returns JSON with song IDs and metadata. Find the `id` field of the target song.

**Fetch lyrics by song ID:**
```
GET https://music.163.com/api/song/lyric?id=SONG_ID&lv=1&kv=1&tv=1
```
Returns JSON with `lrc.lyric` field containing timestamped lyrics.

## Workflow
1. Search to get song ID: `curl -s "https://music.163.com/api/search/get?type=1&s=SONG_NAME&limit=5"`
2. Parse the `id` from results (e.g., `"id":1808053189`)
3. Fetch lyrics: `curl -s "https://music.163.com/api/song/lyric?id=ID&lv=1&kv=1&tv=1"`
4. Extract `lrc.lyric` from response — contains timed lyrics, strip timestamps like `[00:20.414]`

## Quick One-Liner (Song Name → Lyrics)
```bash
id=$(curl -s "https://music.163.com/api/search/get?type=1&s=SONG_NAME&limit=1" | grep -o '"id":[0-9]*' | head -1 | grep -o '[0-9]*')
curl -s "https://music.163.com/api/song/lyric?id=${id}&lv=1&kv=1&tv=1" | grep -o '"lyric":"[^"]*"' | sed 's/"lyric":"//;s/\\n/\n/g;s/"$//' | sed 's/\\r/\n/g' | sed 's/\\/\//g'
```

## Example: 迟迟 (薛之谦)
```bash
# Step 1: Search
curl -s "https://music.163.com/api/search/get?type=1&s=迟迟&limit=5"
# → Found id: 1808053189 (薛之谦's version in 天外来物 album)

# Step 2: Get lyrics
curl -s "https://music.163.com/api/song/lyric?id=1808053189&lv=1&kv=1&tv=1"
```

## Verified Songs
- 迟迟 - 薛之谦 (id: 1808053189, album: 天外来物)

## Why This Works
- Much faster and more reliable than browser scraping
- No bot detection or blocking
- Returns structured JSON with full lyric content
- Works for virtually all Chinese pop songs on NetEase Music

## Fallback: Baidu Baike
If 163 API returns no results, search Baidu Baike:
1. `https://baike.baidu.com/item/SONG_NAME` — most Chinese songs have a Baidu Baike page
2. Baidu Baike pages often contain full lyrics in the article body
3. Use `browser_console` to search for lyric fragments: `document.body.innerText.includes(' lyric fragment ')`

## Pitfalls
- Song names with special characters need URL encoding
- Some songs may have `lrc` version = 0 (no lyrics available)
- Original Mandarin Chinese: use `lv=1`, translated: `tv=1`
