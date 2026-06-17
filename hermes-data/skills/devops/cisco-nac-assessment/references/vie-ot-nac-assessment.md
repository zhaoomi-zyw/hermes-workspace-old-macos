# VIE OT NAC assessment example

This reference captures durable details from a VIE OT NAC assessment workflow. It is an example for future Cisco NAC/Ise assessment tasks, not a one-off status log.

## Inputs used

- ISE export CSV with `Network Device Groups` containing `All Enforcement Modes#All Enforcement Modes#Monitoring` or `#Enforcement`.
- Command-runner text exports per device containing:
  - `show running-config`
  - `show interfaces status`
  - `show interfaces trunk`
  - `show authentication sessions`
  - `show access-session`

## ISE mode parsing

Example field:

```text
Location#All Locations#EU#VIE|IPSEC#Is IPSEC Device#No|Device Type#All Device Types#OT_Switch|All Enforcement Modes#All Enforcement Modes#Monitoring
```

Classification:

- Final `#Monitoring` = NAC Monitoring.
- Final `#Enforcement` = NAC Enforcement.
- No final mode after `All Enforcement Modes#All Enforcement Modes` = Not specified.
- Exclude IOT gateway rows when the requested scope is OT switches.

## IP range simplification example

ISE exports may use host-range syntax such as:

```text
10.225.60.129-254/32#10.225.61.1-126/32#10.225.81.1-126/32
```

For a human summary, these can be simplified as the corresponding /25 site ranges:

```text
10.225.60.128/25
10.225.61.0/25
10.225.81.0/25
```

Caveat: the /25 summary includes the network/broadcast or boundary addresses that may not be in the original host range. For exact ACL-style representation, use `ipaddress.summarize_address_range` instead.

## VIE IE-switch exclusion rule

When assessing VIE IE switches, exclude these before computing NAC gaps:

- `Gi1/1` when it is trunk/uplink.
  - Evidence examples: `show interfaces trunk` shows `Gi1/1 ... trunking`, or `show interfaces status` shows `Gi1/1 Uplink_... connected trunk`.
  - Reason: uplink trunk ports do not require NAC enforcement.
- `Ap1/1` and other internal AP ports.
  - Reason: AP/internal ports are not part of the OT access-port NAC checklist.

After applying this exclusion, classify only the included connected access ports.

## Runtime session nuance

Some IE switches showed MAB authenticated sessions on included access ports even though the parser did not find interface-level NAC commands in `show running-config`.

Use this classification rather than calling them outright failures:

```text
NAC active sessions observed; config not parsed
```

This means the port has runtime MAB/dot1x evidence and needs manual confirmation of why the interface commands were not visible or parsed.

## Good workbook outputs

The most useful workbook shape for business/network review:

1. `Overview` — counts by assessment.
2. `Device Summary` — device result and concise reason.
3. `Interface Detail` — port-level evidence, including exclusion reason.
4. `Export Coverage` — requested device list vs devices actually present in attachments.
5. `Criteria` — rules used for classification.

## Recommended final chat summary

Keep chat output short:

```text
Updated workbook: MEDIA:/path/to/file.xlsx

Summary:
- Total assessed: N
- NAC Enforcement configured: N
- NAC active sessions observed; config not parsed: N
- NAC not configured on included access ports: N
- Not assessed because config was not exported: list...

Rule applied: Gi1/1 trunk/uplink and Ap1/1 were excluded from NAC gap calculation.
```
