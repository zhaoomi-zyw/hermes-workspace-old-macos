---
name: cisco-nac-assessment
description: Assess Cisco switch NAC/802.1X/MAB enforcement status from ISE exports and command-runner outputs; produce concise site/IP-range summaries and Excel workbooks with device/interface evidence.
---

# Cisco NAC Assessment

Use this skill when the user asks to determine whether Cisco switches or ISE network device groups are in NAC Monitoring vs Enforcement, or to summarize why OT/site/IP ranges have not completed NAC enforcement.

## Core workflow

1. Gather the minimum evidence:
   - ISE export CSV / XLSX if available.
   - Switch command outputs, preferably one text export covering:
     - `show running-config`
     - `show interfaces status`
     - `show interfaces trunk`
     - `show authentication sessions`
     - `show access-session`
   - If a command is unsupported, keep the error output as evidence rather than failing the assessment.

2. For ISE export CSVs, identify Monitoring vs Enforcement from the `Network Device Groups` field:
   - `All Enforcement Modes#All Enforcement Modes#Monitoring` means NAC Monitoring.
   - `All Enforcement Modes#All Enforcement Modes#Enforcement` means NAC Enforcement.
   - If the field stops at `All Enforcement Modes#All Enforcement Modes` without a final value, mark it as `Not specified`.
   - Exclude non-OT entries when the user asks for OT switch lists, e.g. device type not equal to `OT_Switch` or obvious `IOT-Devices-GW` rows.

3. For switch command outputs, assess at both device and interface level:
   - Device-level sheet: one row per switch with final assessment, reason/evidence, included connected access port count, excluded port count, active session count, and example NAC ports.
   - Interface-level sheet: one row per port with port status, VLAN, trunk/access/excluded classification, NAC evidence flags, active session count, and config evidence.
   - Coverage sheet: compare the user’s requested device list against devices actually found in the attachment.
   - Criteria sheet: explain the exact classification rules.

## Interface NAC evidence

Treat an included access interface as NAC enforcement configured when it has:

```text
authentication port-control auto
```

or

```text
access-session port-control auto
```

plus at least one of:

```text
mab
dot1x pae authenticator
```

and does not have:

```text
authentication open
```

If `authentication open` is present with NAC commands, classify as `Monitoring/open mode configured`, not strict enforcement.

Runtime evidence also matters:

- `show authentication sessions` or `show access-session` with `mab` or `dot1x` and `Auth` status proves the port is actively participating in NAC.
- If active MAB/dot1x sessions exist but interface-level commands are not visible or not parsed from `show running-config`, do not label it as simply “not configured.” Use: `NAC active sessions observed; config not parsed` and flag for manual review.

## Port exclusions before gap calculation

Do not count these ports as NAC enforcement gaps:

- Trunk/uplink ports from `show interfaces trunk` or `show interfaces status` VLAN column = `trunk`.
- Uplink ports named like `Uplink_*` when they are trunking.
- In VIE IE-switch assessments specifically, `Gi1/1` trunk/uplink should be excluded with reason: `uplink trunk port; NAC not required on trunk/uplink`.
- `Ap1/1` or other internal AP ports should be excluded with reason: `AP/internal port; not part of NAC access-port checklist`.
- Shutdown/disabled/notconnect ports should be reported but not treated the same as active connected access-port gaps.

## Recommended Excel structure

For site/range summaries, keep it simple and filterable:

| Column | Purpose |
|---|---|
| Site | Site code, e.g. `EU#VIE` |
| IP Range / VLAN | Range being assessed |
| Current NAC Mode | ISE/tracking state: Monitoring, Enforcement, No NAC config, etc. |
| Connected Switches | Count from ISE or inventory |
| Switch / Port Type | Short technical context: IE switch, server switch, Honeywell FTE trunk, etc. |
| Reason Category | Standardized reason for missing enforcement |
| Reason / Evidence | One or two short evidence sentences |
| NAC Enforcement Required? | Yes / No / Partial / TBD |
| Next Action / Owner | Who needs to confirm or what needs to change |

For device/interface evidence workbooks, use these sheets:

1. `Overview` — counts by assessment and coverage counts.
2. `Device Summary` — device-level result and reason.
3. `Interface Detail` — per-port evidence and exclusion reason.
4. `Export Coverage` — requested vs actually exported devices.
5. `Criteria` — rules used for the assessment.

## Standard reason categories

Use short, filterable categories instead of long narratives:

- `No active switches / scope to confirm`
- `Removed / obsolete scope`
- `Old template used; technically enforceable after config change`
- `Technical exception - trunk only`
- `Not required - server switches to be renamed`
- `Mixed status / needs split by device type`
- `NAC active sessions observed; config not parsed`
- `NAC not configured on included access ports`

## Reporting style for Omi

For this class of work, keep the final answer concise and operational:

- Provide the Excel file path first.
- Then give a short count summary.
- Then list only the important exceptions or devices needing action.
- Avoid long raw config excerpts in chat; put evidence in the workbook.
- Use plain text/table style suitable for business/network review.

## Pitfalls

- Do not assess NAC purely from `show running-config`; session commands can reveal active NAC even when interface config is hidden, templated, or not parsed.
- Do not treat trunk/uplink ports as missing NAC enforcement.
- Do not treat AP/internal ports as OT access NAC gaps.
- Do not assume the user’s requested device list matches the attachment; always create a coverage check.
- Do not flatten site summaries to port-level detail unless the user explicitly asks; summarize by Site + IP Range/VLAN first, with port evidence in a separate sheet.

## References

- See `references/vie-ot-nac-assessment.md` for a concrete VIE OT/IP range example and classification details learned from a real assessment session.
