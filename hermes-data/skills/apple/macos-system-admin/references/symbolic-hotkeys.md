# Symbolic Hotkeys (com.apple.symbolichotkeys.plist)

Read/write macOS global keyboard shortcuts via Python `plistlib`.

## Read current hotkeys
```python
import plistlib
plist_path = '/Users/<user>/Library/Preferences/com.apple.symbolichotkeys.plist'
with open(plist_path, 'rb') as f:
    data = plistlib.load(f)
hotkeys = data['AppleSymbolicHotKeys']
```

## Set a screenshot shortcut

Key 28 = "Copy picture of selected area to clipboard"

```python
import plistlib, os

plist_path = '/Users/<user>/Library/Preferences/com.apple.symbolichotkeys.plist'
with open(plist_path, 'rb') as f:
    data = plistlib.load(f)

hotkeys = data['AppleSymbolicHotKeys']
hotkeys['28'] = {
    'enabled': True,
    'value': {
        'parameters': [keycode, modifiers, 0],
        'type': 'standard'
    }
}

with open(plist_path, 'wb') as f:
    plistlib.dump(data, f)

os.system('killall SystemUIServer 2>/dev/null')
```

## Remove a shortcut (restore default)
```python
if '28' in hotkeys:
    del hotkeys['28']
```

## Keycodes (common letters)
| Key | Code | Key | Code |
|-----|------|-----|------|
| A   | 0    | Q   | 12   |
| B   | 11   | R   | 15   |
| C   | 8    | S   | 1    |
| D   | 2    | T   | 17   |
| E   | 14   | W   | 13   |
| F   | 3    | 1   | 18   |
| 2   | 19   | 3   | 20   |
| 4   | 21   | 5   | 23   |

## Modifier values
| Modifier | Value   |
|----------|---------|
| Cmd      | 1048576 |
| Shift    | 131072  |
| Option   | 524288  |
| Control  | 262144  |

## Screenshot key IDs
| ID  | Action                            |
|-----|-----------------------------------|
| 28  | Copy selected area to clipboard   |
| 29  | Copy screen to clipboard          |
| 30  | Save selected area to file        |
| 31  | Save screen to file               |

## Pitfalls
- Single-modifier + letter (Option+A) is intercepted by text input system first
- Must use absolute path, not `~/` (Hermes sandboxes home)
- `killall SystemUIServer` needed after changes
- In macOS 26, `defaults write com.apple.universalaccess` is blocked by TCC —
  but `com.apple.symbolichotkeys` is writable via plistlib on file directly
