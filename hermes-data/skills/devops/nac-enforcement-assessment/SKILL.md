---
name: nac-enforcement-assessment
description: Assess Cisco switch NAC enforcement from show command outputs and generate simple Excel summaries for Omi's BI OT/NAC work.
---

# NAC Enforcement Assessment Workflow

Use this skill when Omi provides Cisco switch exports and asks to judge whether NAC enforcement is enabled, why not, or to produce an Excel summary.

## Pre-work: save raw configs

Before analysis, save each switch config dump to a structured directory:

```text
NAC_switch_configs/{SITE}/
├── {SITE}_raw_configs.txt     # Full raw export (can contain multiple devices)
└── {SITE}_NAC_Assessment_Summary.md  # One-page site summary
```

The raw file is the authoritative source. The summary markdown is a quick-reference for Omi's preferred format: Site, device list, current NAC mode, switch/port type, reason/evidence, enforcement required?, and owner/action.

## OT IE switch note (all-trunk design) + LLD v1.3 access VLAN recommendation

Cisco Industrial Ethernet (IE) switches (hostname pattern `BIBNWOTIE-*`) frequently have **all FastEthernet ports configured as trunk ports**, not access ports. This means every connected Fa port is a trunk — there are no "access ports" to assess. The assessment label becomes `No included connected access ports` after excluding trunk ports, even though NAC is configured and active MAB/dot1x sessions exist on those trunk ports.

Do NOT flag these as "NAC not configured" or "no NAC evidence." Note the global template mode explicitly: monitor vs enforcement.

**LLD v1.3 deviation adjustment for these all-trunk OT switches:** Per LLD v1.3 OT access-switch design, non-uplink Fa ports should be converted from trunk to access mode. The **native VLAN ID** currently assigned to each trunk port is the **recommended access VLAN ID** for that port. In the Excel Device Summary's `deviation adjustment` column (Column D), provide a per-port native VLAN → access VLAN mapping:

```
Fa1/1: access VLAN 3573
Fa1/2: access VLAN 3573
Fa1/4: access VLAN 3573
Fa1/5: access VLAN 3574
...
```

**Check for pre-existing `switchport access vlan`:** Some switches already have `switchport access vlan <VLAN>` configured (before `switchport trunk native vlan` in the interface config). When this is present and matches the native VLAN, note it in the recommendation — the access VLAN assignment is complete, only the port mode conversion (trunk→access) remains.

Implementation summary to include:
- Remove `switchport mode trunk`, `switchport trunk native vlan`, `switchport trunk allowed vlan`
- Add `switchport mode access` and `switchport access vlan <native VLAN ID>`
- Keep trunk only on real uplinks (typically Gi1/1, Gi1/2)
- Remove `authentication open` and `access-session template monitor` if enforcement is the target state

**See references:** `references/BIB_G144_OT_IE_assessment_example.md` for a worked example, and `references/BIB_G144_per_port_native_vlan_map.md` for the per-port native VLAN → access VLAN mapping across all 13 G144 switches.

## Parsing Cisco switch config files (common pitfalls)

When reading raw config files from command-runner exports:

### 1. Line endings (`\r\n`)

Cisco config exports often have Windows-style `\r\n` line endings. Python `readlines()` handles this transparently, but **binary-mode or raw-string regex searches will fail** if you use `\n` instead of `\r?\n` or `\s*\r?\n`. Always check with `repr()` before writing regex patterns against raw config text.

### 2. Interface naming: FastEthernet vs Fa

In the running-config, interfaces use the **full name** (`FastEthernet1/1`), while `show interfaces trunk` and `show interfaces status` output use the **abbreviated name** (`Fa1/1`).

- When parsing `show running-config`, match `FastEthernet\d+/\d+` not `Fa\d+/\d+`.
- Convert to short name `Fa` for display and Excel cell cross-referencing.
- The `show interfaces trunk` table output uses the short form `FaX/Y`.

### 3. Optional `switchport access vlan` before `switchport trunk native vlan`

Some IE switches have `switchport access vlan` configured **before** `switchport trunk native vlan` in the same interface block, while others do not. The presence of `switchport access vlan` with the same VLAN ID as the native VLAN means the access VLAN assignment is partly pre-configured — only the port mode needs conversion from trunk to access. Use a regex that handles this optional intermediate line:

```python
pattern = (
    r'interface (FastEthernet\d+/\d+)\s*\r?\n'
    r'(?:\s+switchport access vlan (\d+)\s*\r?\n)?'  # optional
    r'\s+switchport trunk native vlan (\d+)'
)
```

When `group(2)` is not None, the port already has access VLAN pre-configured.

### 4. End of running-config detection

The running-config ends with `end` followed by the device prompt (e.g., `BIBNWOTIE-G144-01-11#`). Section dividers (`---`) and next-command headers follow. Detect end of run config by:

- `line.strip().startswith('<hostname>') and '#' in line` — device prompt
- `line.strip().replace('-', '') == '' and len(line.strip()) > 3` — `---` section divider

## Required / preferred input commands

Preferred full command set per switch:

```text
terminal length 0
show running-config
show interfaces status
show interfaces trunk
show authentication sessions
show access-session
```

If only `show running-config` is available, still assess based on config, but mark the result as `show run only` and set connected/session fields to N/A.

## Key NAC enforcement indicators

Interface-level NAC enforcement is present when an included access port has:

```text
authentication port-control auto
mab
and/or dot1x pae authenticator
```

Also accept newer syntax if present:

```text
access-session port-control auto
```

Monitoring/open mode indicators (interface or global):

```text
authentication open
access-session template monitor    # global — puts ALL ports in monitor mode
```

Global supporting indicators:

```text
aaa new-model
aaa authentication dot1x
aaa authorization network
aaa accounting dot1x
aaa group server radius ...
radius server ...
dot1x system-auth-control
```

## Exclusion rules used in Omi's VIE NAC workbook

Exclude these from NAC gap calculation:

1. Trunk/uplink ports
   - Reason: uplink/trunk ports do not require NAC enforcement.
   - Examples:
     - `Gi1/1` when it is trunk/uplink on IE switches
     - `Gi1/0/24`, `Te1/1/4`, `Te2/1/4` when shown as trunk/uplink

2. AP internal ports
   - Reason: internal AP port is not part of NAC access-port checklist.
   - Examples:
     - `Ap1/1`

3. Disabled / notconnect ports are not active NAC gaps, but still include them in interface detail for evidence when useful.

## Device-level assessment labels

Use these labels consistently:

- `NAC Enforcement configured`
  - All included connected access ports have NAC enforcement config and/or authenticated NAC sessions.

- `NAC Enforcement configured (show run only)`
  - Only show running-config was provided; included access interfaces have NAC enforcement commands, but connected/session evidence is unavailable.

- `NAC active sessions observed; config not parsed`
  - Included connected access ports have authenticated MAB/dot1x sessions, but interface-level NAC commands were not found in parsed show run.

- `NAC not configured on included access ports`
  - Included connected access ports exist, but no NAC config or session evidence was found.

- `No included connected access ports`
  - After excluding trunk/uplink/AP ports, no connected access ports remain for NAC enforcement check.

- `Partial / needs review`
  - Some included connected access ports have NAC evidence, but others lack config/session evidence.

## Excel output format

Generate an `.xlsx` workbook with these sheets:

1. `Overview`
   - Total assessed devices
   - Count by assessment label
   - Requested devices assessed / not assessed
   - Exclusion rule note
   - Latest update note if applicable

2. `Device Summary`
   Recommended columns:
   - Device
   - Assessment
   - Reason / Evidence
   - NAC-configured ports
   - Included connected access ports
   - Connected ports total
   - Notconnect ports
   - Disabled ports
   - Trunk ports
   - Excluded ports count
   - Excluded ports
   - Active NAC sessions
   - Session methods
   - Global dot1x system-auth-control
   - AAA/RADIUS present
   - Example NAC ports

3. `Interface Detail`
   Recommended columns:
   - Device
   - Port
   - Interface
   - Name
   - Port Status
   - VLAN
   - Port Type
   - NAC Assessment
   - Exclusion Reason
   - port-control auto
   - mab
   - dot1x pae authenticator
   - authentication open
   - Active Sessions
   - Session Method
   - Interface Config Evidence

4. `Export Coverage`
   - Category
   - Device
   - Comment
   - Mark devices as requested+assessed, requested but not assessed, or assessed but not in latest requested list.

5. `Criteria`
   - Explain criteria and exclusion rules.

## Style preferences

Keep the workbook simple and filterable. Omi prefers a clear, non-overcomplicated summary that immediately answers:

- Which device/range is NAC enforced?
- Which is not enforced?
- If not enforced, why?
- Which ports were excluded and why?
- Which requested devices are still missing config output?

Use color coding:

- Green: enforcement configured
- Yellow: partial / needs review / show-run-only caveat
- Red: not configured
- Gray: excluded ports
- Blue/light info: no included connected access ports

## VIE 10.225.60.129-254 specific context from 2026-06-15

Workbook created/updated in workspace:

```text
/Users/omi/workspace/VIE-10.225.60.129-254-v2.xlsx
```

Key final rules applied:

- Trunk/uplink ports do not require NAC and are excluded.
- `Ap1/1` is excluded as an internal AP port.
- For `VIENWOT-650-03-01`, trunk/uplink ports `Gi1/0/24`, `Te1/1/4`, and `Te2/1/4` were excluded; 8 included connected access ports had active NAC sessions.
- For `VIENWOTIE-650-04-01`, `Gi1/1` trunk/uplink and `Ap1/1` were excluded; no included connected access ports remained.
