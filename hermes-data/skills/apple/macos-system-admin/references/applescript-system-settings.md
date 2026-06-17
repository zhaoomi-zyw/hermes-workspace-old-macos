# AppleScript UI Automation for System Settings (macOS 26+)

When `defaults write` fails due to TCC protection on macOS 26 Sequoia,
use AppleScript UI scripting to toggle System Settings controls.

## Open a specific settings pane
```bash
# Accessibility → Display
open "x-apple.systempreferences:com.apple.preference.universalaccess?Seeing_Display"

# Display settings
open "x-apple.systempreferences:com.apple.Displays-Settings.extension"

# Keyboard shortcuts
open "x-apple.systempreferences:com.apple.preference.keyboard?Shortcuts"
```

## Core pattern

```bash
osascript -e '
tell application "System Events"
  tell process "System Settings"
    tell window 1
      set allElem to entire contents
      repeat with e in allElem
        try
          if class of e is checkbox and name of e contains "降低透明度" then
            click e
            return "Clicked " & (name of e) & ", new value = " & (value of e)
          end if
        end try
      end repeat
    end tell
  end tell
end tell'
```

## Common element types
- `checkbox` — toggle switches (has `value` property: 0 or 1)
- `pop up button` — dropdown menus (has `value` property)
- `radio group` — radio button sets
- `button` — clickable buttons
- `static text` — labels (use `name` to read page title)

## Discover page contents
```bash
osascript -e '
tell application "System Events"
  tell process "System Settings"
    tell window 1
      set pageTitle to name of static text 1
      set allElem to entire contents
      set outputStr to "Page: " & pageTitle
      repeat with e in allElem
        try
          set c to class of e as string
          if c is "pop up button" then
            set outputStr to outputStr & "\nPOPUP: " & (name of e) & " = " & (value of e)
          else if c is "checkbox" then
            set outputStr to outputStr & "\nCHECKBOX: " & (name of e) & " = " & (value of e)
          else if c is "radio group" then
            set outputStr to outputStr & "\nRADIO: " & (name of e)
          end if
        end try
      end repeat
      return outputStr
    end tell
  end tell
end tell'
```

## Read a popup button's menu
```bash
osascript -e '
tell application "System Events"
  tell process "System Settings"
    tell window 1
      repeat with e in (entire contents)
        if class of e is pop up button and name of e is "用途" then
          click e; delay 0.5
          set items to ""
          tell menu 1 of e
            repeat with mi in every menu item
              set items to items & (name of mi) & "\n"
            end repeat
          end tell
          key code 53  -- Escape to close menu
          return items
        end if
      end repeat
    end tell
  end tell
end tell'
```

## Pitfalls

- `entire contents` on a window with many nested elements can time out
  after 15s. Use targeted queries when possible.
- The variable name `result` is a reserved word in AppleScript.
- `System Events` needs Accessibility permission. If it returns empty
  results, the permission may be missing.
- `keystroke` commands require additional permissions and are often
  blocked in newer macOS. Prefer `click` on UI elements instead.
- System Settings UI hierarchy changes between macOS versions. Test
  element names on the target OS.
- After toggling a setting, verify by re-reading the element's value.
