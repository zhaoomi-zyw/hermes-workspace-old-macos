# macOS Accessibility Settings GUI Automation

On macOS Sequoia (26+), `defaults write com.apple.universalaccess` is blocked by TCC (Transparency, Consent, and Control). The plist exists at `/Users/<user>/Library/Preferences/com.apple.universalaccess.plist` and is **readable** but **not directly writable** via `defaults` or `plutil`. AppleScript GUI automation via System Events is the workaround.

## Prerequisites

System Events must have Accessibility permission (System Settings → Privacy & Security → Accessibility). If `osascript` returns errors about "not allowed to send keystrokes", the permission is missing.

## Pattern 1: Navigate to Settings Pane

```bash
# Accessibility → Display
open "x-apple.systempreferences:com.apple.preference.universalaccess?Seeing_Display"

# Displays (monitor settings)
open "x-apple.systempreferences:com.apple.Displays-Settings.extension"
```

## Pattern 2: Check Current Page

```applescript
tell application "System Events"
    tell process "System Settings"
        tell window 1
            try
                return name of static text 1  -- page title
            end try
        end tell
    end tell
end tell
```

## Pattern 3: Find and Toggle a Specific Checkbox

This is the canonical pattern. Uses `entire contents` to search the full UI tree, then clicks by name match.

```applescript
tell application "System Events"
    tell process "System Settings"
        tell window 1
            set allElem to entire contents
            repeat with e in allElem
                try
                    if class of e is checkbox and (name of e) contains "降低透明度" then
                        click e
                        return "Clicked " & (name of e) & ", new value = " & (value of e)
                    end if
                end try
            end repeat
        end tell
    end tell
end tell
```

**Names to match by** (Chinese localization):
- "降低透明度" = Reduce Transparency
- "增强对比度" = Increase Contrast
- "减弱动态效果" = Reduce Motion
- "原彩显示" = True Tone
- "自动调节亮度" = Auto-Brightness

## Pattern 4: Read Popup Button Values

```applescript
tell application "System Events"
    tell process "System Settings"
        tell window 1
            set allElem to entire contents
            repeat with e in allElem
                try
                    if class of e is pop up button then
                        -- (name of e) & " = " & (value of e)
                    end if
                end try
            end repeat
        end tell
    end tell
end tell
```

## Pattern 5: Click a Popup Button and Read Menu Items

```applescript
tell application "System Events"
    tell process "System Settings"
        tell window 1
            set allElem to entire contents
            repeat with e in allElem
                try
                    if class of e is pop up button and name of e is "颜色描述文件" then
                        click e
                        delay 0.3
                        tell menu 1 of e
                            repeat with mi in every menu item
                                -- (name of mi)
                            end repeat
                        end tell
                        key code 53  -- Escape to close
                    end if
                end try
            end repeat
        end tell
    end tell
end tell
```

## Common Popup Names

- "颜色描述文件" = Color Profile
- "用途" = Use As (Main/Extended/Mirror)
- "刷新率" = Refresh Rate

## Pitfalls

1. **`result` is a reserved word** in AppleScript — don't use it as a variable name. Use `outputStr`, `ret`, etc.

2. **UI tree depth**: Settings windows in macOS 26 have deeply nested groups (group → splitter group → group → splitter → group...). `entire contents` flattens this, which is why it works when direct traversal fails.

3. **Timeout on large trees**: `entire contents` can have 500+ elements. Searches may timeout (>15s). Be specific in name matching to avoid full scans.

4. **`key code` needs accessibility permission**: `key code 53` (Escape) to dismiss popup menus requires the same permission as clicking.

5. **Setting value may not update instantly**: After clicking a checkbox, re-read the element's value to confirm the change took effect.

## Real-World Case: Reduce Transparency Toggle (Sequoia 26.4.1)

1. Opened: `open "x-apple.systempreferences:com.apple.preference.universalaccess?Seeing_Display"`
2. Verified page: "显示" (Display) — the sub-pane of Accessibility
3. Found checkbox "降低透明度" with value 0
4. Clicked it → value became 1
5. WindowServer CPU dropped from 32.5% → 23.2%

The plist at `/Users/omi/Library/Preferences/com.apple.universalaccess.plist` showed `reduceTransparency => true` after the change, confirming GUI changes are reflected in the plist — it's just the write path that's TCC-protected.
