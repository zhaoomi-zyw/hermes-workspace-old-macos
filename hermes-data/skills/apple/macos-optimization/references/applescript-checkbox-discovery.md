# macOS Accessibility Checkbox Discovery

When you need to find what accessibility checkboxes exist on the current
System Settings page and their current state (on=1, off=0):

```applescript
osascript -e '
tell application "System Events"
    tell process "System Settings"
        tell window 1
            set allElem to entire contents
            set outputStr to ""
            repeat with e in allElem
                if class of e is checkbox then
                    try
                        set outputStr to outputStr & (name of e) & " = " & (value of e) & "\n"
                    end try
                end if
            end repeat
            if outputStr is "" then set outputStr to "no checkboxes found"
            return outputStr
        end tell
    end tell
end tell'
```

To scope by keyword (e.g., find transparency-related checkboxes only):

```applescript
osascript -e '
tell application "System Events"
    tell process "System Settings"
        tell window 1
            set allElem to entire contents
            set outputStr to ""
            repeat with e in allElem
                if class of e is checkbox then
                    try
                        set n to name of e
                        if n contains "透明" or n contains "对比" then
                            set outputStr to outputStr & n & " = " & (value of e) & "\n"
                        end if
                    end try
                end if
            end repeat
            if outputStr is "" then set outputStr to "none found"
            return outputStr
        end tell
    end tell
end tell'
```

## Discover all popup buttons and checkboxes

```applescript
osascript -e '
tell application "System Events"
    tell process "System Settings"
        tell window 1
            set allElem to entire contents
            set outputStr to ""
            repeat with e in allElem
                try
                    set c to class of e as string
                    if c is "pop up button" then
                        set outputStr to outputStr & "POPUP: " & (name of e) & " = " & (value of e) & "\n"
                    else if c is "checkbox" then
                        set outputStr to outputStr & "CHECKBOX: " & (name of e) & " = " & (value of e) & "\n"
                    end if
                end try
            end repeat
            return outputStr
        end tell
    end tell
end tell'
```

## Common issue: page title discovery

To check what page Settings is currently showing:

```applescript
osascript -e '
tell application "System Events"
    tell process "System Settings"
        tell window 1
            return name of static text 1
        end tell
    end tell
end tell'
```

The static text at position 1 in the window usually holds the current page title
(e.g., "显示", "辅助功能", "墙纸"). If it returns empty, you may be on the wrong page
or the title element is nested deeper.

## Display settings — discover which display is being configured

Display Settings shows config for one display at a time. To check which display:

```applescript
osascript -e '
tell application "System Events"
    tell process "System Settings"
        tell window 1
            set allElem to entire contents
            repeat with e in allElem
                try
                    if class of e is pop up button and name of e is "用途" then
                        return "用途 = " & (value of e)  -- e.g. "主显示器", "扩展显示器"
                    end if
                end try
            end repeat
            return "用途 popup not found"
        end tell
    end tell
end tell'
```

To switch which display is configured, click the visual display icons
at the top of the Display Settings window (not scriptable — guide the user manually).
