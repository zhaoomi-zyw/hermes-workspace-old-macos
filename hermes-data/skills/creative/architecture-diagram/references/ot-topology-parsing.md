# OT Network Topology — Data Parsing Recipe

## Source Formats

Two common input formats from Boehringer OT network audits:

### 1. Command Runner `.txt` Output
Multi-device dump from Cisco IOS: `show lldp neighbors detail`, `show cdp neighbors detail`, `show interfaces status`, `show running-config`.

**File structure:**
```
==============Device : LMJNWOTHON-B40-01-01P.eu.boehringer.com (FQDN)==============
---------------------------------------
command: show lldp neighbors detail
status: SUCCESS
output:
<raw CLI output>
---------------------------------------
command: show running-config
...
==============Device : next-device...
```

**Parsing approach (Python):**
```python
import re

with open('command_runner.txt', 'r') as f:
    content = f.read()

# Split by device headers
headers = list(re.finditer(r'==============Device : (.+?)==============', content))

for i, h in enumerate(headers):
    start = h.end()
    end = headers[i+1].start() if i+1 < len(headers) else len(content)
    section = content[start:end]
    
    # Key extraction patterns
    cfg_hostname = re.search(r'hostname\s+(\S+)', section)  # configured hostname
    model = re.search(r'switch \d+ provision (\S+)', section)  # C9300-48S, etc.
    vlans = re.findall(r'vlan\s+(\d+)\s*\n\s*name\s+(\S+)', section)  # VLAN ID + name
    aaa = re.search(r'aaa authentication login default\s+(.+)', section)  # AAA method
    radius = re.findall(r'server\s+name\s+(\S+)', section)  # ISE PSN servers
    stp = re.search(r'spanning-tree mode\s+(\S+)', section)
    mgmt = re.search(r'interface Vlan(\d+).*?ip address (\S+)', section, re.DOTALL)
    
    # CDP neighbors
    cdp_devices = re.findall(r'Device ID[:\s]+(\S+)', section)
    cdp_local_ints = re.findall(r'Interface[:\s]+(.+?)[,\n]', section)
    cdp_remote_ports = re.findall(r'Port ID \(outgoing port\)[:\s]+(.+)', section)
    cdp_platforms = re.findall(r'Platform[:\s]+(.+?),', section)
    
    # LLDP neighbors (per-entry parsing)
    lldp_entries = section.split('Local Intf:')[1:]  # skip preamble
    for entry in lldp_entries:
        local_intf = entry.split('\n')[0].strip()
        sys_name = re.search(r'System Name[:\s]+(\S+)', entry)
        port_id = re.search(r'Port id[:\s]+(\S+)', entry)
        port_desc = re.search(r'Port Description[:\s]+(.+?)\n', entry)
        mgmt_ip = re.search(r'Management Addresses.*?\n\s+IP[:\s]+(\S+)', entry, re.DOTALL)
    
    # Interface status — connected ports only
    connected = re.findall(r'^(\S+/\S+(?:/\S+)?(?:/\S+)?)\s+(\S+.*?)\s+connected', section, re.MULTILINE)
```

**Common pitfalls:**
- LLDP sysName may be "- not advertised" for HPE/Aruba devices (MAC-only chassis IDs, e.g. `507c.6f59.xxxx`)
- `show cdp neighbors detail` may fail with "Authentication failed" on some switches
- Some devices have both CDP and LLDP for the same neighbor → deduplicate by link pair
- Running-config has ~45K bytes; regex needs `re.DOTALL` for multi-line matches

### 2. Excel Workbook (`.xlsx`)
Multi-sheet topology workbook. Typical sheets:

| Sheet | Content |
|-------|---------|
| `Physical_Links` | All links (uplink + endpoint), 14 columns |
| `Endpoint_Links` | OT endpoint only, with System Description (device model) |
| `Uplink_Links` | Core uplinks only, with remote port and IP |
| `Summary_By_Device` | Per-switch: endpoint count + uplink count |
| `Interface_Details` | Every interface: status, VLAN, NAC, port config |
| `All_CDP_LLDP_Neighbors` | Raw CDP/LLDP output per interface |
| `Layout_Notes` | Diagram layout decisions |

**Excel parsing (openpyxl):**
```python
import openpyxl
wb = openpyxl.load_workbook('topology.xlsx', data_only=True)
for sheet_name in wb.sheetnames:
    ws = wb[sheet_name]
    for row in ws.iter_rows(min_row=2, values_only=True):
        # row is a tuple: (local_device, local_hostname, local_interface, remote_device, ...)
```

**Device type extraction from System Description:**
```python
def classify_endpoint(sysdesc):
    if 'CPU 1516F' in sysdesc: return 'PLC CPU 1516F-3 (Safety)'
    if 'CPU 1516' in sysdesc: return 'PLC CPU 1516-3'
    if 'CPU 1517' in sysdesc: return 'PLC CPU 1517-3'
    if 'CPU 1515' in sysdesc: return 'PLC CPU 1515-2'
    if 'CP 1543' in sysdesc: return 'CP 1543-1 (Comm Processor)'
    if 'SCALANCE S615' in sysdesc: return 'SCALANCE S615 (Security)'
    if 'Thin Client' in sysdesc: return 'Thin Client'
    if 'HMI' in sysdesc or 'TP700' in sysdesc or 'TP1200' in sysdesc: return 'HMI Panel'
    if 'Panel' in remote: return 'Operator Panel'
    return 'Unknown'
```

## Typical Boehringer OT Naming Conventions

| Pattern | Meaning |
|---------|---------|
| `BIBNCOT-*` | Core OT switches (C9500) |
| `BIBNWOTIE-*` | IE (Industrial Ethernet) switches |
| `LMJNCOT-*` | LMJ Core OT switches |
| `LMJNWOTHON-*` | LMJ OT Network (ON) switches |
| `LMJNWOTHONEV-*` | LMJ OT Network EV (EV) switches |
| `B30-*` | Aggregation layer |
| `B40-*` | Access layer |
| `-01P` / `-02P` | Stack standby (passive) unit |
| `BIBOD*TC` | Industrial Thin Client |
| `pg*` | HMI Panel hostname |

## Typical VLAN Patterns

**IE (G144):** VLAN 3573 (OT Control, PLCs) + VLAN 3574 (OT HMI, Panels/TCs)
**LMJ ON:** VLAN 824/825 + VLAN 1024 (Traffic) + VLAN 1150 (Mgmt)
**LMJ EV:** VLAN 823/826 + VLAN 1023 (Traffic) + VLAN 501 (HiveAP) + VLAN 1150 (Mgmt)
**Common:** VLAN 1150 = OT_MGMT across all sites; 802.1X+MAB with ISE RADIUS

## Endpoint Archetypes

### Siemens S7 PLCs (VLAN 3573 / 10.160.179.0/24)
- LLDP: System Name not advertised, Chassis ID = `psg-plc` or MAC
- Port: `port-001` with Description like "Siemens, SIMATIC S7, Ethernet Port, X2 P1"
- OID: `1.3.6.1.4.1.24686` (Siemens Automation)
- Capabilities: `B,S` (Bridge, Station)
- Speed: 100base-TX(FD)

### Siemens Thin Clients (VLAN 3574 / 10.160.180.0/24)
- LLDP: hostname `BIBOD*TC`, Port: `port-001`
- Description: "Siemens, Ethernet Port 1, 1000 Mbit, Full duplex, link"
- System Description: "Siemens, SIMATIC PC Station, Industrial Thin Client, 6AV6 646-..."
- Capabilities: `O` (Other)

### HPE/Aruba APs (LMJ, MAC-only)
- LLDP: sysName not advertised, Chassis ID = MAC address (507c.6fxx = HPE OUI)
- No IP in LLDP Management Addresses
- Connected to Gi1/0/x ports on aggregation and access switches
- Typically 6 per switch on Gi1/0/1-3 and Gi1/0/11-13
