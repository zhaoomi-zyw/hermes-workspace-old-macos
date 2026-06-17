# G144 IE Switch Topology (BIB Site)

Reference topology generated 2026-05-29 for the BIB G144 industrial Ethernet network.

## Architecture

### Core Layer (2 switches)
| Hostname | IP | Model | Role |
|----------|-----|-------|------|
| BIBNCOT-G144-01-0501P | 10.160.219.6 | — | Core · Active |
| BIBNCOT-G144-01-0502P | 10.160.219.7 | — | Core · Standby |

### IE Switch Layer (13 switches — collapsed two-tier, all dual-homed to cores)
| Hostname | Uplinks | Downlinks |
|----------|---------|-----------|
| G144-U1-01 | 2 | 1 |
| G144-01-01 | 2 | 3 |
| G144-01-02 | 2 | 2 |
| G144-01-03 | 2 | 2 |
| G144-01-04 | 2 | 2 |
| G144-01-05 | 2 | 3 |
| G144-01-06 | 2 | 1 |
| G144-01-08 | 2 | 1 |
| G144-01-09 | 2 | 3 |
| G144-01-10 | 2 | 2 |
| G144-01-11 | 2 | 2 |
| G144-01-12 | 2 | 1 |
| G144-02-01 | 2 | 2 |

### Key Correction from Excel Data
The original PDF showed a three-tier (Core → Distribution → Access) layout, but the Excel physical links data confirmed ALL 13 IE switches connect directly to BOTH core switches — this is a **collapsed two-tier** architecture, not three-tier.

### OT Endpoints
33 LLDP-discovered endpoints across two subnets:
- 10.160.179.0/24
- 10.160.180.0/24

Device types: CPU 1516-3, CPU 1517-3, CPU 1515-2, CP1543-1, SCALANCE S615, Thin Clients, HMIs, Panels.

2 unknown endpoints (MAC-only, no sysName).

### VLAN
VLAN 3573 and 3574 used for endpoint access ports.

## Source Files
- `BIB_G144_IE_Physical_Topology_Optimized.pdf` — original Visio-style PDF
- `BIB_G144_IE_Physical_Topology_Optimized.xlsx` — Excel with Physical_Links and Endpoint_Links sheets (authoritative for port mappings)

## Generated Output
- `BIB_G144_IE_Topology.html` — dark-themed SVG (first pass, pre-Excel correction — has wrong three-tier layout)
