# macOS Keyboard Keycodes

Keycodes used in `com.apple.symbolichotkeys.plist` → `parameters[0]`.

| Key | Keycode | Key | Keycode |
|-----|---------|-----|---------|
| A   | 0       | N   | 45      |
| B   | 11      | O   | 31      |
| C   | 8       | P   | 35      |
| D   | 2       | Q   | 12      |
| E   | 14      | R   | 15      |
| F   | 3       | S   | 1       |
| G   | 5       | T   | 17      |
| H   | 4       | U   | 32      |
| I   | 34      | V   | 9       |
| J   | 38      | W   | 13      |
| K   | 40      | X   | 7       |
| L   | 37      | Y   | 16      |
| M   | 46      | Z   | 6       |

| Number | Keycode | F-Key | Keycode |
|--------|---------|-------|---------|
| 0      | 29      | F1    | 122     |
| 1      | 18      | F2    | 120     |
| 2      | 19      | F3    | 99      |
| 3      | 20      | F4    | 118     |
| 4      | 21      | F5    | 96      |
| 5      | 23      | F6    | 97      |
| 6      | 22      | F7    | 98      |
| 7      | 26      | F8    | 100     |
| 8      | 28      | F9    | 101     |
| 9      | 25      | F10   | 109     |
|        |         | F11   | 103     |
|        |         | F12   | 111     |

| Symbol   | Keycode | Symbol | Keycode |
|----------|---------|--------|---------|
| Space    | 49      | Tab    | 48      |
| Return   | 36      | Escape | 53      |
| Delete   | 51      | Fwd Del| 117     |
| Up       | 126     | Down   | 125     |
| Left     | 123     | Right  | 124     |

## Modifiers (additive, stored in parameters[1])

| Modifier | Value    |
|----------|----------|
| Command  | 1048576  |
| Shift    | 131072   |
| Option   | 524288   |
| Control  | 262144   |
| Caps Lock| 65536    |
| Fn       | 8388608  |

Example: Cmd+Shift = 1048576 + 131072 = 1179648
Example: Cmd+Option+Ctrl = 1048576 + 524288 + 262144 = 1835008
