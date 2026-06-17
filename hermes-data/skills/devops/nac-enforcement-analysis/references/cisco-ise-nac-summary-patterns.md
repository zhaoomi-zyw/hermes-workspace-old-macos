# Cisco ISE NAC Summary Patterns

Session context: user was summarizing OT switch/site ranges that had not completed NAC enforcement and needed a simple reason-based summary, not a complex port-level report.

## Cisco ISE Network Device CSV

In `exportNetworkDeviceType*.csv`, the export did not include a dedicated `NAC Mode` column. The useful field was:

```text
Network Device Groups:String(100)(Type#Root Name#Name|...):Required
```

The mode was encoded as:

```text
All Enforcement Modes#All Enforcement Modes#Monitoring
All Enforcement Modes#All Enforcement Modes#Enforcement
```

Parsing rule:

```python
import re
m = re.search(r'All Enforcement Modes#All Enforcement Modes#([^|]+)', ndg)
mode = m.group(1).strip() if m else 'Not specified'
```

If the text only has `All Enforcement Modes#All Enforcement Modes` without a final mode, treat it as `Not specified / cannot determine from this table`.

## Example monitoring rows from the session

The Cisco ISE CSV showed these as `Monitoring`:

| Name | Site | Description | IP Range |
|---|---|---|---|
| OT_ATS_Switches | AM#ATS | ATS OT Switches VLAN1150 | 10.1.114.129-254/32 |
| OT_BCN_Switches | EU#BCN | BCN OT Switches VLAN1101 | 10.1.32.129-190/32 |
| OT_BIB_Switches | EU#BIB | BIB OT Switches | 10.160.215.1-254/32#10.160.216-231.0-254/32 |
| OT_LMJ_Switches | EU#LMJ | LMJ OT Switches VLAN1150 | 10.1.20.129-254/32 |
| OT_STP_Switches | EU#STP | STP OT Switches VLAN1101 | 10.1.19.129-254/32 |
| OT_VIE_Switches | EU#VIE | VIE OT Switches VLAN1150-1151-1154 | 10.225.60.129-254/32#10.225.61.1-126/32#10.225.81.1-126/32 |

## Example enforcement rows from the session

The Cisco ISE CSV showed 20 rows as `Enforcement`, mostly ING ranges and HEW/YAM, e.g.:

- `OT_HEW_Switches_NAC` — EU#HEW — `10.1.10.1-62/32`
- `OT_LAN_ING_2032B_Switches_NAC` — EU#ING — `10.176.191.0-126/32`
- `OT_LAN_ING_2342_Switches_NAC` — EU#ING — `10.176.194.128-254/32`
- `OT_YAM_Switches` — AP#YAM — `10.1.144.65-126/32`

## Excel workbook patterns

The workbook had multiple sheets including a high-level table plus site-specific evidence sheets:

- A top-level sheet with columns like `Site in ISE`, `IP range`, `Site`, `ISE NAC Mode`, `Connected Switches`, `comment`.
- BIB trunk analysis sheet with connected trunk ports.
- VIE inventory and VIE not-enforced port detail sheets.

For the management summary, aggregate by `Site + IP Range/VLAN`, not by every interface.

## Useful summary column set

Use this simple column set for Omi's NAC reporting:

| Column | Purpose |
|---|---|
| Site | Site code from ISE/reporting scope |
| IP Range / VLAN | Range being explained; include VLAN if known |
| Current NAC Mode | Monitoring, Enforcement, Monitoring/trunk, No NAC configuration, N/A |
| Connected Switches | Count of switches in the range |
| Switch / Port Type | Short technical context, e.g. IE switches/trunk, Honeywell FTE, server switches |
| Reason Category | Standardized simple reason for filtering |
| Reason / Evidence | 1–2 sentences, no raw port dump |
| NAC Enforcement Required? | Yes / No / Partial / TBD |
| Next Action / Owner | Who confirms or what happens next |

## Session-derived classification examples

| Site | IP Range | Suggested classification |
|---|---|---|
| AM#ATS | 10.1.114.128/25 | 0 connected switches; confirm if scope still needed |
| EU#BCN | N/A / VLAN1101 or VLAN1150 depending source | Removed/obsolete; clean up tracking if confirmed |
| EU#BIB | 10.160.215/216 ranges | 0 connected switches in summary; validate active scope |
| EU#BIB | 10.160.219.0/25 | Old IE template/trunk; technically enforceable after changing template/port mode |
| EU#LMJ | 10.1.20.128/25 | Honeywell FTE trunk-only; likely technical exception |
| EU#STP | 10.1.19.128/25 | 0 connected switches; TBD / confirm scope |
| EU#VIE | 10.225.60.128/25 | Mixed device types; split by device type before final decision |
| EU#VIE | 10.225.61.0/24 | 0 connected switches; TBD / confirm scope |
| EU#VIE | 10.225.81.0/25 | Mixed: some enforced, some Honeywell FTE/no NAC; confirm with site owner |
| EU#VIE | 172.20.232.128/25 | Server switches to be renamed; if confirmed, no NAC needed |
| EU#VIE | 172.20.233.0/25 | Server switches to be renamed; if confirmed, no NAC needed |

## Wording pattern

```text
The non-enforced NAC scope is summarized at Site + IP Range/VLAN level instead of individual switchport level. For each range, the table identifies the current NAC mode, number of connected switches, switch/port type, the reason why NAC enforcement is not currently applied, whether enforcement is actually required, and the next owner/action.

The purpose is to separate real enforcement gaps from valid exceptions, obsolete ranges, and ranges requiring further site validation.
```
