# BIB G144 — OT IE All-Trunk Site Assessment Example

Use this as a reference when assessing NAC on Cisco IE switches where all FastEthernet ports are in trunk mode.

## Site summary

| Field | Value |
|-------|-------|
| Site | BIB G144 (OT Industrial Ethernet) |
| Devices | 13 x Cisco Catalyst IE (IOS 15.2) |
| Hostname pattern | BIBNWOTIE-G144-{rack}-{NN} |
| Config last changed | 2026-06-03 by x2breitema4pa |
| Source file | NAC_switch_configs/BIB_G144/BIB_G144_raw_configs.txt |
| Related Excel | BIB_G144_NAC_Analysis_with_deviation_adjustment_v3.xlsx (D column updated with per-port native VLAN → access VLAN recommendation per LLD v1.3) |
| Per-port VLAN map | `references/BIB_G144_per_port_native_vlan_map.md` |

## Common NAC config (all 13 switches)

- AAA: `aaa new-model` with RADIUS group `RG_ISE_NAC`
- ISE servers: BIBAS00253 (148.192.144.45), INHNXISEPSN2 (10.183.175.69)
- `dot1x system-auth-control` enabled
- Device sensor: CDP/LLDP/DHCP profiling for ISE
- **`access-session template monitor`** — global monitor mode (not enforcing)

## Interface NAC config (all Fa ports)

All FastEthernet ports are trunk ports with:
- `authentication port-control auto` ✓
- `mab` ✓
- `dot1x pae authenticator` ✓
- `authentication open` (monitor mode — allows traffic even if auth fails)
- `authentication host-mode multi-auth`
- `authentication order dot1x mab`

## Assessment label: No included connected access ports

Because ALL Fa ports are trunks, after excluding trunk/uplink ports, **no connected access ports remain** for NAC gap calculation. The connected ports are:
- Fa1/4, Fa1/5 — trunk (connected to downstream devices)
- Gi1/1, Gi1/2 — uplink trunk

This is NOT "NAC not configured" — NAC is fully configured, ISE is reachable, and active MAB sessions exist:
- Fa1/4: 2 x MAB authenticated sessions (ec1c.5d77.d768, ec1c.5d77.d769)
- Fa1/5: 1 x MAB authenticated session (3013.8922.3d0d)

## The real gap

The open issue is the **global monitor template** (`access-session template monitor`). To move to enforcement, this must be changed to `closed` or `low-impact`, and `authentication open` removed from interfaces.

## VLAN scope

Active VLANs across site: 1, 7, 178-181, 190-194, 484, 600, 690, 1128 (mgmt), 1158 (mgmt), 1618, 1721, 2202, 3082, 3128, 3159, 3163, 3189-3190, 3199, 3241, 3271, 3301, 3409, 3423, 3429, 3442-3444, 3475, 3481, 3512, 3543, 3545, 3547, 3551, 3568, 3573-3574, 3600, 4091
