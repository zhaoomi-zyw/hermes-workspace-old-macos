# TP-Link Router API Notes

## TL-XDR3050 (and similar Wi-Fi 6 TP-Link routers)

### Web UI Architecture
- Uses Canvas-based rendering — **headless browsers CANNOT navigate the UI** (Canvas accessibility tree is empty)
- JavaScript files are loadable without auth from `/web-static/`:
  - `/web-static/lib/ajax.js` — AJAX framework, contains `orgURL()` and `load()` functions
  - `/web-static/dynaform/app.js` — main app
  - `/web-static/dynaform/menu.js` — menu structure with page URLs
  - `/web-static/dynaform/class.js` — core classes

### Authentication Flow
1. Router stores `publicKey` (RSA), `lgKey`, `encryptType` in `sessionStorage`
2. Password is RSA-encrypted before sending
3. After login, stok is stored in `$.session` (a JavaScript global)
4. All API calls go through `$.orgURL(path)` which returns `/stok=<encoded_stok>/<path>`

### Getting the stok from browser console
```javascript
// After logging in through normal browser:
$.session  // returns the stok token
```

### Common API endpoints (from menu.js)
| Menu Key | URL | Description |
|----------|-----|-------------|
| flowManage_rsMenu | FlowManage.htm | Flow management/traffic stats |
| behaviorMgt_rsMenu | BehaviorCon.htm | Behavior management |
| lanSet_rsMenu | LanCfg.htm | LAN/DHCP settings |
| network_rsMenu | WanCfg.htm | WAN config |
| dhcpServer_rsMenu | DHCPServer.htm | DHCP server |

### API call format
```
POST /stok=<stok>/ds
Content-Type: application/json; charset=UTF-8

{"method":"get", "network": {"flow_statistic": {}}}
```

### Limitations
- **The stok is tied to the browser session** — curl with the same stok may return -40101
- **Consumer TP-Link routers do NOT track per-device historical traffic** — even if you get the API working, the data isn't there
- The FlowManage page (if it exists) likely shows real-time traffic only, not 13-day history
- Error codes: -40401 (invalid stok), -40101 (unauthorized), -40210 (method not found)

### Getting Connected Devices (Fallback)
```bash
# ARP table from any connected device
arp -a | grep -v incomplete | grep -v 255$

# MAC OUI identification
# f8:ce:21 = TP-Link
# 3c:22:fb = Apple
# Randomized MACs have bit 1 of first byte set (e.g., 8e:xx, 36:xx, 2e:xx)
```
