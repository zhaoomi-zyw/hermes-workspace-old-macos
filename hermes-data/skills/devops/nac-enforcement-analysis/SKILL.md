---
name: nac-enforcement-analysis
description: Analyze Cisco ISE / NAC enforcement vs monitoring exports and produce clear site/IP-range summary tables for OT switch NAC gap tracking.
triggers:
  - Cisco ISE NAC export CSV or Excel analysis
  - NAC enforcement vs monitoring status summary
  - OT switch NAC gap reporting by site, IP range, or VLAN
  - Explain why site/range is not NAC enforced
---

# NAC Enforcement Analysis

Use this skill when the user is analyzing Cisco ISE / NAC data, especially OT switch ranges that are in Monitoring, Enforcement, or have no NAC configuration.

## Core workflow

1. Inspect the source file structure first.
   - For Excel: list sheet names, headers, and sample rows.
   - For CSV exports from Cisco ISE Network Device Type: inspect headers and parse `Network Device Groups`.

2. Determine the level of summary before writing.
   - Prefer `Site + IP Range/VLAN` level for management summaries.
   - Do not default to per-port detail unless the user explicitly asks for port-level remediation.
   - Port-level evidence is supporting detail, not the main summary.

3. For each Site/IP range, classify the situation into a small number of reason categories.
   Recommended categories:
   - `No active switches / scope to confirm`
   - `Removed / obsolete scope`
   - `Old template used; technically enforceable after config change`
   - `Technical exception - trunk only`
   - `Not required - server switches to be renamed`
   - `Mixed status / needs split by device type`
   - `TBD / needs site validation`

4. Keep the summary table simple and filterable.
   Recommended columns:
   - `Site`
   - `IP Range / VLAN`
   - `Current NAC Mode`
   - `Connected Switches`
   - `Switch / Port Type`
   - `Reason Category`
   - `Reason / Evidence`
   - `NAC Enforcement Required?`
   - `Next Action / Owner`

5. Separate real gaps from exceptions.
   - `Yes`: should be enforced, but blocked by configuration/template/implementation.
   - `No`: valid exception, obsolete range, or non-scope switch type.
   - `Partial`: same range contains multiple situations.
   - `TBD`: insufficient data; site/network owner must validate.

## Cisco ISE CSV mode detection

In Cisco ISE Network Device export CSVs, NAC mode may not have a dedicated `NAC Mode` column. It can be encoded in:

`Network Device Groups:String(100)(Type#Root Name#Name|...):Required`

Pattern examples:

```text
All Enforcement Modes#All Enforcement Modes#Monitoring
All Enforcement Modes#All Enforcement Modes#Enforcement
```

Rule:
- Contains `All Enforcement Modes#All Enforcement Modes#Monitoring` -> NAC Monitoring
- Contains `All Enforcement Modes#All Enforcement Modes#Enforcement` -> NAC Enforcement
- Has `All Enforcement Modes#All Enforcement Modes` but no final mode -> `Not specified / cannot determine from this table`

Use a regex like:

```python
re.search(r'All Enforcement Modes#All Enforcement Modes#([^|]+)', network_device_groups)
```

## Switch configuration assessment

When the user exports switch command output to verify whether NAC enforcement is actually configured, ask for or parse these commands per device:

```text
show running-config
show interfaces status
show interfaces trunk
show authentication sessions
show access-session
```

Use `show running-config` for configuration intent, `show interfaces status` and `show interfaces trunk` to avoid misclassifying trunks/disabled/notconnect ports as gaps, and `show authentication sessions` / `show access-session` for runtime evidence.

Interface-level enforcement criteria:

- `NAC Enforcement configured`: interface has `authentication port-control auto` or `access-session port-control auto`, plus `mab` and/or `dot1x pae authenticator`, and does **not** have `authentication open`.
- `Monitoring/open mode configured`: interface has NAC commands but also has `authentication open`.
- `NAC not configured`: access interface lacks port-control/access-session plus MAB/dot1x authenticator commands.
- `Not applicable - trunk`: port is listed in `show interfaces trunk` or appears as `trunk` in `show interfaces status`.

For Excel output, include both a device-level sheet and an interface-level evidence sheet. Also include an export-coverage sheet comparing requested hostnames vs devices actually present in the command-runner output; this avoids silently treating missing device exports as non-enforced.

### BI IT4OT LLD v1.3 non-uplink trunk-port deviation pattern

When analyzing BI IT4OT OT switches, compare non-uplink ports against the relevant LLD before calling them NAC gaps, but do not assume every trunk access-facing port is a Honeywell FTE exception.

Decision rule:

- Exclude true uplinks from the NAC check as usual.
- If the device/port is explicitly confirmed as Honeywell FTE, the BI-IT4OT-LAN products LLD v1.3 FTE section may apply: FTE access ports can be trunk ports and NAC is not used / not activated on Honeywell FTE switchports.
- If the ports are **not** Honeywell FTE access ports, the FTE exception does **not** apply. Non-uplink user/device ports configured as trunk should be treated as an LLD/template deviation and recommended for conversion to standard OT Access-Switch access-port configuration.

For non-FTE non-uplink trunk ports, recommend:

- convert from trunk to access mode: `switchport mode access`, `switchport access vlan <target access VLAN>`;
- remove trunk native/allowed VLAN configuration from those access-facing ports;
- keep standard access-port hardening from LLD: `spanning-tree portfast`, `spanning-tree bpduguard enable`, storm-control broadcast/multicast, `no snmp trap link-status` where applicable;
- after converting to access mode, apply/keep NAC enforcement on access ports (`authentication`/`access-session port-control auto`, `mab` and/or `dot1x pae authenticator` as required) and remove monitoring/open-mode if the target state is enforcement;
- keep only real uplinks as excluded trunk ports and validate the target access VLAN per connected OT endpoint before implementation.

For Device Summary Excel work, a useful pattern is to insert a `deviation adjustment` column after `Reason / Evidence`, aggregate `Interface Detail` by device, and write one concise device-level recommendation rather than dumping raw port configs.

## Reporting style for Omi

For BI/enterprise network reporting, Omi prefers concise, practical, readable summaries. Avoid over-complicated tables and avoid dumping raw switchport config into the main summary. The goal is to make it obvious why a site or IP range is not enforced and what action is needed.

Good summary wording:

```text
The non-enforced NAC scope is summarized at Site + IP Range/VLAN level instead of individual switchport level. For each range, the table identifies the current NAC mode, number of connected switches, switch/port type, the reason why NAC enforcement is not currently applied, whether enforcement is actually required, and the next owner/action.

The purpose is to separate real enforcement gaps from valid exceptions, obsolete ranges, and ranges requiring further site validation.
```

## Pitfalls

- Do not treat every `Not configured` port as a real NAC gap. Disabled/notconnect ports, trunks, server switches, Honeywell FTE switches, and obsolete ranges may be exceptions or out of scope.
- Do not collapse VIE-like sites into one simple reason when different IP ranges contain different device types.
- Do not assume `Connected Switches = 0` means complete; classify as scope confirmation / possible cleanup.
- For BIB-like old-template cases, distinguish `currently monitoring/trunk` from `technically enforceable after changing template/port mode`.

## References

- `references/cisco-ise-nac-summary-patterns.md` — session-derived patterns for Cisco ISE NAC exports, including BIB/VIE examples and CSV parsing rules.
- `references/switch-config-enforcement-assessment.md` — command-output parsing criteria for judging whether Cisco switch interfaces have NAC enforcement configured, including recommended Excel sheets and export coverage checks.
