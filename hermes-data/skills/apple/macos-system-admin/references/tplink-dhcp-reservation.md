# TP-Link LAN IP reservation pattern

Use this when a macOS host is pinned to a LAN IP and the user wants the router to reserve/bind the same IP so DHCP does not hand it to another device.

## Example from TL-XDR3050

Target host:
- Wi-Fi MAC: `3c:22:fb:54:bc:d5`
- Static/reserved IP: `192.168.1.109`
- Router: `192.168.1.1`
- Router model observed: TP-Link TL-XDR3050

## Workflow

1. Verify current Mac interface details before changing router state:
   ```bash
   networksetup -getinfo Wi-Fi
   route -n get default
   ```
2. Log into router web UI, usually `http://192.168.1.1`.
3. For TL-XDR3050 firmware, the DHCP reservation UI may not be under DHCP Server. It can be under:
   - 应用管理 → 已安装应用 → IP与MAC绑定
4. In `IP与MAC绑定设置`, add a row with:
   - Host/name: a readable label such as `Hermes-Mac`
   - MAC: TP-Link UI accepts uppercase hyphen form, e.g. `3C-22-FB-54-BC-D5`
   - IP: target LAN IP, e.g. `192.168.1.109`
5. Save the row. If a direct DOM value assignment clears on save, fill the fields via normal browser typing events (`browser_type`) and click 保存.
6. Verify router-side state:
   - The row appears in `IP与MAC绑定设置` as a normal saved row, not an edit row.
   - In `IP与MAC映射表`, the device row shows 状态 = `绑定`.
7. Verify Mac-side network still works:
   ```bash
   networksetup -getinfo Wi-Fi | sed -n '1,8p'
   route -n get default | awk '/gateway|interface/ {print}'
   curl -I --connect-timeout 5 --max-time 10 https://www.apple.com 2>/dev/null | head -n 1
   ```

## Pitfalls

- TP-Link calls the feature `IP与MAC绑定`; it is effectively an address reservation plus ARP binding, not always labelled `DHCP 地址保留`.
- The current device may be on a later page of `IP与MAC映射表`; use the binding settings table to add manually if the visible page does not show it.
- A router-side binding does not replace the macOS network setting. For a truly fixed address, use both: macOS static/manual IP and router IP-MAC binding/reservation.
- After changing network settings, an ICMP ping to the router may briefly fail while routing/ARP refreshes. Confirm with route table, router HTTP response, DNS, and external HTTPS before declaring failure.
