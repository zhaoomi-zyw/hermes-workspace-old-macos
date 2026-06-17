# Switch Config NAC Enforcement Assessment

Use this reference when the user provides Cisco switch command-runner output and asks whether NAC enforcement is configured.

## Required command outputs

Minimum useful set per switch:

```text
show running-config
show interfaces status
show interfaces trunk
show authentication sessions
show access-session
```

`show running-config` alone can prove whether NAC commands exist, but cannot safely distinguish active access gaps from trunks, uplinks, shutdown, or unused ports. Always use status/trunk output when deciding why a switch or port is not enforced.

## Interface criteria

Treat an access interface as NAC enforcement configured when it has:

```text
authentication port-control auto
```

or newer syntax:

```text
access-session port-control auto
```

plus at least one authentication method:

```text
mab
dot1x pae authenticator
```

and it does **not** contain:

```text
authentication open
```

Classifications:

| Classification | Evidence |
|---|---|
| NAC Enforcement configured | `authentication port-control auto` or `access-session port-control auto` + `mab` and/or `dot1x pae authenticator`, no `authentication open` |
| Monitoring/open mode configured | NAC commands exist but `authentication open` is present |
| NAC not configured | Access interface lacks port-control/access-session + MAB/dot1x authenticator commands |
| Not applicable - trunk | Port appears in `show interfaces trunk` or VLAN/status shows trunk |
| Not applicable - unused | Port is shutdown/disabled/notconnect and no active endpoint is present; do not count as active enforcement gap unless the user wants future-state config compliance |

Runtime evidence from `show authentication sessions` or `show access-session` is helpful but not required for configuration enforcement. A port can be correctly configured with no active session if no endpoint is connected.

## Excel output pattern

Create at least these sheets:

1. `Device Summary`
   - Device
   - Assessment
   - Reason if not enforced / Evidence
   - NAC-configured ports
   - Connected access ports
   - Connected ports total
   - Notconnect ports
   - Disabled ports
   - Trunk ports
   - Active NAC sessions
   - Session methods
   - Global dot1x system-auth-control
   - AAA/RADIUS present
   - Example NAC ports

2. `Interface Detail`
   - Device
   - Port
   - Interface
   - Name
   - Port Status
   - VLAN
   - Port Type
   - NAC Assessment
   - port-control auto
   - mab
   - dot1x pae authenticator
   - authentication open
   - Active Sessions
   - Session Method
   - Interface Config Evidence

3. `Export Coverage`
   - Category
   - Device
   - Comment

Use the export coverage sheet whenever the user provided a requested device list. Mark devices as:

- `Requested and exported`
- `Requested but NOT exported` — cannot assess from current attachment
- `Exported but not in requested list`

This prevents missing command output from being misreported as a NAC gap.

## Session example

A command-runner export covering 9 VIE devices showed:

- 8 devices had enforcement configured on access interfaces, typically 40 NAC-configured ports each.
- 1 device (`VIENWOT-017-U1-01`) had no interface-level NAC enforcement commands and no active authentication/access sessions.
- Several requested devices were absent from the attachment; they were listed in `Export Coverage` as not assessable rather than classified as non-enforced.

The key reason for `NAC not configured` was absence of interface-level commands such as:

```text
authentication port-control auto
mab
dot1x pae authenticator
```

while enforced devices had interface blocks like:

```text
interface GigabitEthernet1/0/1
 switchport access vlan 938
 switchport mode access
 authentication control-direction in
 authentication event fail action next-method
 authentication host-mode multi-auth
 authentication order dot1x mab
 authentication priority dot1x mab
 authentication port-control auto
 authentication periodic
 mab
 dot1x pae authenticator
```
