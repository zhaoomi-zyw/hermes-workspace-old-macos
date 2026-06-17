# Parsing Cisco Command Runner Output

## File Structure

Command Runner output is a concatenation of multiple device sessions:

```
==============Device : hostname.fqdn (hostname.fqdn)==============

---------------------------------------
command: show lldp neighbors detail
status: SUCCESS
output:
... LLDP data ...

---------------------------------------
command: show cdp neighbors detail
status: SUCCESS
output:
... CDP data ...

---------------------------------------
command: show interfaces status
status: SUCCESS
output:
... interface status table ...

---------------------------------------
command: show running-config
status: SUCCESS
output:
... full running config ...
```

## Python Parsing Recipe

### 1. Split into device sections

```python
import re

with open("command_runner_output.txt", "r") as f:
    content = f.read()

# Find all device header positions
headers = list(re.finditer(r'==============Device : (.+?)==============', content))

for i, h in enumerate(headers):
    hostname_full = h.group(1).strip()
    short = hostname_full.split('(')[0].strip().replace('.eu.boehringer.com', '')
    
    start = h.end()
    end = headers[i+1].start() if i+1 < len(headers) else len(content)
    section = content[start:end]
    # ... parse commands below
```

### 2. Extract running-config info

```python
cfg = re.search(r'hostname\s+(\S+)', section)
cfg_name = cfg.group(1) if cfg else short

model = re.search(r'switch \d+ provision (\S+)', section)
model_str = model.group(1) if model else "Unknown"
```

### 3. Extract CDP neighbors

CDP detail output is unstructured, multiline. Key fields appear in sequence:

```
Device ID: LMJNWOTHONEV-B30-00-01.eu.boehringer.com
...
IP address: 10.195.155.2
Platform: cisco C9300-48S,  Capabilities: ...
Interface: TenGigabitEthernet1/1/4,  Port ID (outgoing port): TenGigabitEthernet1/1/1
```

Parse approach: isolate the CDP output block, then extract fields:

```python
cdp_start = section.find('command: show cdp neighbors detail')
if cdp_start >= 0:
    output_start = section.find('output:', cdp_start)
    next_cmd = section.find('command:', output_start + 1)
    if next_cmd < 0:
        next_cmd = len(section)
    cdp_text = section[output_start:next_cmd]

if cdp_text and 'FAILURE' not in cdp_text[:200]:
    cdp_devices = re.findall(r'Device ID[:\s]+(\S+)', cdp_text)
    local_ints = re.findall(r'Interface[:\s]+(.+?)[,\n]', cdp_text)
    remote_ports = re.findall(r'Port ID \(outgoing port\)[:\s]+(.+)', cdp_text)
    platforms = re.findall(r'Platform[:\s]+(.+?),', cdp_text)
    
    for j in range(min(len(cdp_devices), len(local_ints))):
        # cdp_devices[j], local_ints[j], remote_ports[j], platforms[j]
```

### 4. Extract LLDP neighbors

LLDP detail output is per-neighbor blocks starting with `Local Intf:`:

```
Local Intf: Te1/1/1
Local Intf service instance: -
Chassis id: a410.b6c5.3b00
Port id: Te1/1/4
Port Description: Uplink_1_LMJNWOTHONEV-B30-00-01
System Name: LMJNWOTHONEV-B40-01-02P.eu.boehringer.com
...
Management Addresses:
    IP: 10.1.20.135
```

Parse approach:

```python
lldp_start = section.find('command: show lldp neighbors detail')
# ... same isolation pattern as CDP ...

entries = lldp_text.split('Local Intf:')
for entry in entries[1:]:
    local_intf = entry.split('\n')[0].strip()
    sys_name_m = re.search(r'System Name[:\s]+(\S+)', entry)
    port_id_m = re.search(r'Port id[:\s]+(\S+)', entry)
    port_desc_m = re.search(r'Port Description[:\s]+(.+?)\n', entry)
    mgmt_m = re.search(r'Management Addresses.*?\n\s+IP[:\s]+(\S+)', entry, re.DOTALL)
    
    if sys_name_m:
        sys_name = sys_name_m.group(1).replace('.eu.boehringer.com', '')
        desc = port_desc_m.group(1).strip() if port_desc_m else ""
        # port_id_m.group(1), mgmt_m.group(1), etc.
```

### 5. Extract interface status

```python
intf_lines = re.findall(
    r'^(\S+/\S+(?:/\S+)?(?:/\S+)?)\s+(\S+.*?)\s+connected',
    section, re.MULTILINE
)
# Returns list of (port, description) tuples for connected ports only
```

## Port Description Conventions (BI Network)

LLDP port descriptions encode the link role:

| Format | Meaning |
|--------|---------|
| `Uplink_1_HOSTNAME` | Primary uplink between access and aggregation |
| `Downlink_HOSTNAME` | Downlink from aggregation/core to access |
| `Crosslink` | Direct connection between stack primary switches (bypassing aggregation) |

## Common Pitfalls

- CDP and LLDP see the same physical link → deduplicate by (device_a, device_b) pair
- LLDP may show MAC-only entries (sysName = `-`) for unmanaged devices (HPE/Aruba APs, cameras, etc.)
- Interface status `connected` counts include uplinks — cross-reference with CDP/LLDP to separate uplinks from downlinks
- Some devices will have `status: FAILURE` with `Authentication failed` — skip parsing, mark as "Auth Failed"
