# BIB G144 — Per-Port Native VLAN → Access VLAN Mapping

Source: `NAC_switch_configs/BIB_G144/BIB_G144_raw_configs.txt`
Related Excel: `/Users/omi/workspace/BIB_G144_NAC_Analysis_with_deviation_adjustment_v3.xlsx`
Generated: 2026-06-16

All 13 IE switches use native VLANs **3573** or **3574** across their FastEthernet ports. Per LLD v1.3, the native VLAN ID becomes the recommended access VLAN ID when converting from trunk to access mode.

## Devices WITH `switchport access vlan` already pre-configured

These switches already have `switchport access vlan <VLAN>` in the running-config (matching the native VLAN). Only port-mode conversion (trunk→access) is needed.

### BIBNWOTIE-G144-01-08 (8 ports, all pre-configured)

| Port | Native VLAN | Access VLAN (pre-configured) |
|------|-------------|------------------------------|
| Fa1/1 | 3573 | 3573 |
| Fa1/2 | 3574 | 3574 |
| Fa1/3 | 3573 | 3573 |
| Fa1/4 | 3573 | 3573 |
| Fa1/5 | 3574 | 3574 |
| Fa1/6 | 3573 | 3573 |
| Fa1/7 | 3573 | 3573 |
| Fa1/8 | 3573 | 3573 |

### BIBNWOTIE-G144-01-09 (8 ports, all pre-configured)

| Port | Native VLAN | Access VLAN (pre-configured) |
|------|-------------|------------------------------|
| Fa1/1 | 3573 | 3573 |
| Fa1/2 | 3573 | 3573 |
| Fa1/3 | 3573 | 3573 |
| Fa1/4 | 3573 | 3573 |
| Fa1/5 | 3574 | 3574 |
| Fa1/6 | 3574 | 3574 |
| Fa1/7 | 3574 | 3574 |
| Fa1/8 | 3574 | 3574 |

### BIBNWOTIE-G144-01-12 (8 ports, all pre-configured)

| Port | Native VLAN | Access VLAN (pre-configured) |
|------|-------------|------------------------------|
| Fa1/1 | 3573 | 3573 |
| Fa1/2 | 3573 | 3573 |
| Fa1/3 | 3573 | 3573 |
| Fa1/4 | 3573 | 3573 |
| Fa1/5 | 3574 | 3574 |
| Fa1/6 | 3574 | 3574 |
| Fa1/7 | 3574 | 3574 |
| Fa1/8 | 3574 | 3574 |

### BIBNWOTIE-G144-02-01 (7 ports, all pre-configured)

Note: No Fa1/2 on this switch.

| Port | Native VLAN | Access VLAN (pre-configured) |
|------|-------------|------------------------------|
| Fa1/1 | 3573 | 3573 |
| Fa1/3 | 3573 | 3573 |
| Fa1/4 | 3573 | 3573 |
| Fa1/5 | 3574 | 3574 |
| Fa1/6 | 3574 | 3574 |
| Fa1/7 | 3574 | 3574 |
| Fa1/8 | 3574 | 3574 |

## Devices WITHOUT `switchport access vlan` pre-configured

These switches need both the `switchport access vlan` addition AND the trunk→access mode conversion.

### BIBNWOTIE-G144-01-01

| Port | Native VLAN | Recommended Access VLAN |
|------|-------------|-------------------------|
| Fa1/1 | 3573 | 3573 |
| Fa1/2 | 3573 | 3573 |
| Fa1/3 | 3573 | 3573 |
| Fa1/4 | 3573 | 3573 |
| Fa1/5 | 3574 | 3574 |
| Fa1/6 | 3573 | 3573 |
| Fa1/7 | 3573 | 3573 |
| Fa1/8 | 3573 | 3573 |

### BIBNWOTIE-G144-01-02

| Port | Native VLAN | Recommended Access VLAN |
|------|-------------|-------------------------|
| Fa1/1 | 3573 | 3573 |
| Fa1/2 | 3573 | 3573 |
| Fa1/3 | 3573 | 3573 |
| Fa1/4 | 3573 | 3573 |
| Fa1/5 | 3574 | 3574 |
| Fa1/6 | 3574 | 3574 |
| Fa1/7 | 3574 | 3574 |
| Fa1/8 | 3574 | 3574 |

### BIBNWOTIE-G144-01-03

| Port | Native VLAN | Recommended Access VLAN |
|------|-------------|-------------------------|
| Fa1/1 | 3573 | 3573 |
| Fa1/2 | 3573 | 3573 |
| Fa1/3 | 3573 | 3573 |
| Fa1/4 | 3573 | 3573 |
| Fa1/5 | 3574 | 3574 |
| Fa1/6 | 3574 | 3574 |
| Fa1/7 | 3574 | 3574 |
| Fa1/8 | 3574 | 3574 |

### BIBNWOTIE-G144-01-04

| Port | Native VLAN | Recommended Access VLAN |
|------|-------------|-------------------------|
| Fa1/1 | 3573 | 3573 |
| Fa1/2 | 3573 | 3573 |
| Fa1/3 | 3573 | 3573 |
| Fa1/4 | 3573 | 3573 |
| Fa1/5 | 3574 | 3574 |
| Fa1/6 | 3574 | 3574 |
| Fa1/7 | 3574 | 3574 |
| Fa1/8 | 3574 | 3574 |

### BIBNWOTIE-G144-01-05 (16 ports — largest switch)

| Port | Native VLAN | Recommended Access VLAN |
|------|-------------|-------------------------|
| Fa1/1 | 3573 | 3573 |
| Fa1/2 | 3573 | 3573 |
| Fa1/3 | 3573 | 3573 |
| Fa1/4 | 3573 | 3573 |
| Fa1/5 | 3574 | 3574 |
| Fa1/6 | 3574 | 3574 |
| Fa1/7 | 3574 | 3574 |
| Fa1/8 | 3573 | 3573 |
| Fa1/9 | 3573 | 3573 |
| Fa1/10 | 3573 | 3573 |
| Fa1/11 | 3573 | 3573 |
| Fa1/12 | 3573 | 3573 |
| Fa1/13 | 3574 | 3574 |
| Fa1/14 | 3573 | 3573 |
| Fa1/15 | 3573 | 3573 |
| Fa1/16 | 3573 | 3573 |

### BIBNWOTIE-G144-01-06

| Port | Native VLAN | Recommended Access VLAN |
|------|-------------|-------------------------|
| Fa1/1 | 3573 | 3573 |
| Fa1/2 | 3573 | 3573 |
| Fa1/3 | 3573 | 3573 |
| Fa1/4 | 3573 | 3573 |
| Fa1/5 | 3574 | 3574 |
| Fa1/6 | 3574 | 3574 |
| Fa1/7 | 3574 | 3574 |
| Fa1/8 | 3573 | 3573 |

### BIBNWOTIE-G144-01-10

| Port | Native VLAN | Recommended Access VLAN |
|------|-------------|-------------------------|
| Fa1/1 | 3573 | 3573 |
| Fa1/2 | 3573 | 3573 |
| Fa1/3 | 3574 | 3574 |
| Fa1/4 | 3573 | 3573 |
| Fa1/5 | 3574 | 3574 |
| Fa1/6 | 3573 | 3573 |
| Fa1/7 | 3573 | 3573 |
| Fa1/8 | 3573 | 3573 |

### BIBNWOTIE-G144-01-11

| Port | Native VLAN | Recommended Access VLAN |
|------|-------------|-------------------------|
| Fa1/1 | 3573 | 3573 |
| Fa1/2 | 3573 | 3573 |
| Fa1/3 | 3573 | 3573 |
| Fa1/4 | 3573 | 3573 |
| Fa1/5 | 3574 | 3574 |
| Fa1/6 | 3574 | 3574 |
| Fa1/7 | 3574 | 3574 |
| Fa1/8 | 3574 | 3574 |

### BIBNWOTIE-G144-U1-01 (7 ports — no Fa1/1)

| Port | Native VLAN | Recommended Access VLAN |
|------|-------------|-------------------------|
| Fa1/2 | 3573 | 3573 |
| Fa1/3 | 3573 | 3573 |
| Fa1/4 | 3573 | 3573 |
| Fa1/5 | 3574 | 3574 |
| Fa1/6 | 3574 | 3574 |
| Fa1/7 | 3574 | 3574 |
| Fa1/8 | 3574 | 3574 |
