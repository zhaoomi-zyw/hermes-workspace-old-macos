---
name: weather-aqi-fetch
description: Get current weather and AQI data for Chinese cities using wttr.in + waqi.info APIs (fallback when weather.com fails)
category: data-science
tags: [weather, api, china, aqi]
---

# Weather + AQI Data Fetch Skill

## Trigger
Need to get current weather and air quality data for a Chinese city when weather.com or qweather.com fail/redirect incorrectly.

## Weather Data — wttr.in

```python
from hermes_tools import terminal
import json

result = terminal(command='curl -s "https://wttr.in/Shanghai?format=j1" 2>/dev/null')
data = json.loads(result['output'])

curr = data['current_condition'][0]
# Keys: temp_C, FeelsLikeC, humidity, windspeedKmph, visibility, uvIndex, weatherDesc[0]["value"], pressure
```

**Important**: JSON keys use `tempC` (no underscore) — NOT `temp_C`. Hourly `time` is integer like `900` = 9:00 AM.

## AQI Data — waqi.info

```python
result = terminal(command='curl -s "https://api.waqi.info/feed/shanghai/?token=demo" 2>/dev/null')
data = json.loads(result['output'])
# Keys: data["aqi"], data["iaqi"]["pm25"]["v"], data["dominentpol"]
```

Replace city name in URL (e.g., `beijing`, `guangzhou`). Token `demo` works for basic access.

## Verified Working URLs
- Weather: `https://wttr.in/{city}?format=j1`
- AQI: `https://api.waqi.info/feed/{city}/?token=demo`

## Issues Encountered
- weather.com redirects Chinese city searches to wrong locations (e.g., Shanghai → Nanjing Xuanwu District)
- qweather.com 404s on direct URL paths
- wttr.in is reliable and returns complete data including feels-like, humidity, wind, UV, visibility

## Output Template
```
📍 {city} 今日天气
🌡️ 温度/体感温度: {temp_C}°C / {FeelsLikeC}°C
💧 湿度: {humidity}%
🌬️ 空气: AQI {aqi} ({dominant_pollutant})
☁️ 天气: {weather_desc}
```
