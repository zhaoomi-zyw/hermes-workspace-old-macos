# Codex Chrome Extension

## Key Facts

- **Chrome Web Store URL**: `https://chromewebstore.google.com/detail/codex/hehggadaopoacecdllhhajmbjkdcmajg`
- **Extension ID**: `hehggadaopoacecdllhhajmbjkdcmajg`
- **Native host name**: `com.openai.codexextension`
- **Distribution**: Exclusively through Codex Desktop App (App → Plugins → Chrome). NOT in the `@openai/codex` npm package.
- **Compatibility**: Codex Desktop App only. Does NOT work with Codex CLI standalone.

## Installation (Official Path)

1. Open Codex Desktop App
2. Go to **Plugins**
3. Add the **Chrome** plugin
4. Follow the guided setup — App installs the extension and handles permissions
5. Open Chrome, confirm the extension shows **Connected**

## Windows: Native Messaging Host Registry Pitfall

Known issue (GitHub #24040): Even after installation, the Windows registry key may be missing:

```
HKCU\Software\Google\Chrome\NativeMessagingHosts\com.openai.codexextension
```

The manifest file exists at `%LOCALAPPDATA%\OpenAI\extension\com.openai.codexextension.json` but Chrome can't discover it without the registry key.

**Fix**: In Codex App, remove and re-add the Chrome plugin from Plugins. If that fails, the registry key must be created manually pointing to the manifest file.

**Diagnostic**: Run the bundled checker to verify:
```
node <codex-home>\plugins\cache\openai-bundled\chrome\<version>\scripts\check-native-host-manifest.js --json
```

## Architecture Note

The Chrome Extension is a bridge — it has no standalone function. It relays browser page content/DOM/screenshots to the Codex App, and relays control commands (click, type, scroll) back to Chrome. Without the Codex App running, the extension does nothing.
