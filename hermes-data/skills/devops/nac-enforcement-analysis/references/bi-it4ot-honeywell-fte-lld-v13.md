# BI IT4OT LLD v1.3 — Honeywell FTE NAC adjustment pattern

Use this reference when analyzing BI IT4OT OT switch exports where non-uplink ports are Honeywell FTE access ports configured as trunks.

## Authoritative LLD points captured from session

Source document used in the session: `BI-IT4OT-LAN products LOW LEVEL DESIGN VERSION 1.3`.

Relevant Honeywell FTE guidance:

- Honeywell FTE access ports require two VLANs: FTE primary VLAN and IOHive VLAN.
- Therefore most FTE access ports are configured as trunk ports, with the FTE primary VLAN as native VLAN.
- The LLD explicitly states: `NAC is not used at FTE switches` / `NAC is not activated on Honeywell FTE switchports`.
- FTE access port template includes trunk native/allowed VLANs, `switchport block unicast`, `storm-control`, `spanning-tree bpduguard enable`, `spanning-tree portfast trunk`, `cdp enable`, `ip dhcp snooping trust`, and `no shutdown`.

## Analysis rule

When a device/range appears to be Honeywell FTE scope:

1. Do not treat non-uplink FTE trunk access ports as ordinary access ports requiring NAC enforcement.
2. If those trunk FTE ports contain NAC/open-mode template commands such as:
   - `authentication open`
   - `authentication order dot1x mab`
   - `authentication priority dot1x mab`
   - `authentication port-control auto`
   - `mab`
   - `dot1x pae authenticator`
   then classify this as an LLD/template deviation, not as proof that FTE should be NAC-enforced.
3. Keep true uplinks excluded from NAC checks.
4. Recommend aligning FTE switchports to the LLD FTE access-port template and validating native/allowed VLANs plus Honeywell ACL/QoS separately.

## Suggested Excel wording

For a device-level `deviation adjustment` column:

```text
LLD v1.3 deviation: This device appears to be Honeywell FTE scope. Per LLD v1.3 Honeywell FTE section, FTE access ports are trunk ports and "NAC is not used at FTE switches". Current non-uplink physical ports show NAC/open-mode template on <n>/<total> ports, including connected ports <ports> with active NAC session evidence on <ports>. Recommended adjustment: do not count these FTE trunk access ports as NAC enforcement-required gaps; instead align the FTE access-port template to LLD: trunk native/allowed FTE + IOHive VLANs, switchport block unicast, bpduguard, spanning-tree portfast trunk, ip dhcp snooping trust, and remove/avoid NAC commands (authentication open/order/priority/port-control, mab, dot1x pae authenticator) on FTE switchports. Keep Gi uplinks excluded; validate native/allowed VLANs and Honeywell ACL/QoS separately.
```

If no connected non-uplink physical ports are observed, append:

```text
No connected non-uplink physical ports were observed, so treat as template cleanup / future-port standardization rather than live remediation.
```

## Excel edit pattern used successfully

- Insert the new column immediately after C on `Device Summary`.
- Header: `deviation adjustment`.
- Use `Interface Detail` to aggregate by device:
  - exclude physical ports whose type/name/evidence indicates uplink trunk;
  - inspect remaining physical ports for connected status, active sessions, trunk mode, and NAC commands;
  - write a device-level concise recommendation rather than raw port-level dumps.
- Reopen the workbook after saving and verify:
  - `Device Summary` has the expected new column count;
  - D1 is `deviation adjustment`;
  - no device rows have blank adjustment text.
