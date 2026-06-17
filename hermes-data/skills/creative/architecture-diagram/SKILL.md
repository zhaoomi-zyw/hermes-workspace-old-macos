---
name: architecture-diagram
description: "Dark-themed SVG architecture/cloud/infra diagrams as HTML."
version: 1.0.0
author: Cocoon AI (hello@cocoon-ai.com), ported by Hermes Agent
license: MIT
dependencies: []
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [architecture, diagrams, SVG, HTML, visualization, infrastructure, cloud]
    related_skills: [concept-diagrams, excalidraw]
---

# Architecture Diagram Skill

Generate professional, dark-themed technical architecture diagrams as standalone HTML files with inline SVG graphics. No external tools, no API keys, no rendering libraries — just write the HTML file and open it in a browser.

## Scope

**Best suited for:**
- Software system architecture (frontend / backend / database layers)
- Cloud infrastructure (VPC, regions, subnets, managed services)
- Microservice / service-mesh topology
- Database + API map, deployment diagrams
- **OT/Industrial network topology** — physical (switch-level) and logical (VLAN, IP plan, device types)
- Anything with a tech-infra subject that fits a grid-backed aesthetic

**Two theme variants — ask or auto-detect:**
- **Dark theme (default):** Slate-950 (`#020617`) background — best for software/cloud/SaaS architecture.
- **Light theme:** White/`#f0f4f8` background — best for network topology, enterprise IT, corporate presentations, or when user says "浅色背景" / "light background" / "corporate style".

**Look elsewhere first for:**
- Physics, chemistry, math, biology, or other scientific subjects
- Physical objects (vehicles, hardware, anatomy, cross-sections)
- Floor plans, narrative journeys, educational / textbook-style visuals
- Hand-drawn whiteboard sketches (consider `excalidraw`)
- Animated explainers (consider an animation skill)

If a more specialized skill is available for the subject, prefer that.

Based on [Cocoon AI's architecture-diagram-generator](https://github.com/Cocoon-AI/architecture-diagram-generator) (MIT).

## Workflow

1. User describes their system architecture (components, connections, technologies)
2. Generate the HTML file following the design system below
3. Save with `write_file` to a `.html` file (e.g. `~/architecture-diagram.html`)
4. User opens in any browser — works offline, no dependencies

### Output Location

Save diagrams to a user-specified path, or default to the current working directory:
```
./[project-name]-architecture.html
```

### Preview

After saving, suggest the user open it:
```bash
# macOS
open ./my-architecture.html
# Linux
xdg-open ./my-architecture.html
```

## Design System & Visual Language

### Color Palette (Semantic Mapping)

Use specific `rgba` fills and hex strokes to categorize components:

| Component Type | Fill (rgba) | Stroke (Hex) |
| :--- | :--- | :--- |
| **Frontend** | `rgba(8, 51, 68, 0.4)` | `#22d3ee` (cyan-400) |
| **Backend** | `rgba(6, 78, 59, 0.4)` | `#34d399` (emerald-400) |
| **Database** | `rgba(76, 29, 149, 0.4)` | `#a78bfa` (violet-400) |
| **AWS/Cloud** | `rgba(120, 53, 15, 0.3)` | `#fbbf24` (amber-400) |
| **Security** | `rgba(136, 19, 55, 0.4)` | `#fb7185` (rose-400) |
| **Message Bus** | `rgba(251, 146, 60, 0.3)` | `#fb923c` (orange-400) |
| **External** | `rgba(30, 41, 59, 0.5)` | `#94a3b8` (slate-400) |

### Typography & Background
- **Font:** JetBrains Mono (Monospace), loaded from Google Fonts
- **Sizes:** 12px (Names), 9px (Sublabels), 8px (Annotations), 7px (Tiny labels)
- **Background:** Slate-950 (`#020617`) with a subtle 40px grid pattern

```svg
<!-- Background Grid Pattern -->
<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e293b" stroke-width="0.5"/>
</pattern>
```

### Light Theme Variant (corporate / IT / network)

When the user requests "浅色背景", "light theme", "corporate", or the diagram is for enterprise IT / OT network topology, switch to:

**Background:** `#f0f4f8` page body, `#ffffff` diagram card
**Grid:** `#f1f5f9` grid lines on white
**Text:** `#1e293b` (dark slate) for primary, `#475569` for secondary, `#64748b` for tertiary
**Font:** Same JetBrains Mono, but sizes: 11px names, 9px labels, 8px sublabels, 7px annotations

**Light Theme Color Palette (for network/IT):**

| Layer / Role | Box Fill | Box Stroke | Badge Fill |
| :--- | :--- | :--- | :--- |
| **Core** | `#1e40af` (solid blue) | `#1e3a8a` | — |
| **Aggregation** | `#0d9488` (solid teal) | `#0f766e` | — |
| **Access** | `#ffffff` + colored stroke | `#16a34a` (ON) / `#7c3aed` (EV) | Colored header bar |
| **Stack/Standby** | `#f8fafc` | `#8b5cf6` (dashed) | — |
| **Endpoints** | `#fffbeb` (amber-50) | `#d97706` | — |
| **Alert/Warning** | `#fff1f2` (rose-50) | `#e11d48` | — |
| **VLAN/Subnet** | `#f5f3ff` (violet-50) | `#7c3aed` | — |
| **Mgmt Plane** | `#ecfeff` (cyan-50) | `#0891b2` | — |

**Light theme zone boundaries:** Use `fill="rgba(R,G,B,0.04)"` with matching stroke and `stroke-dasharray="5,3"`. Labels inside zone rects use the zone's stroke color at `font-size="9" font-weight="600"`.

**Light theme card:** `<div class="diagram-container">` gets `background: #ffffff; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.06)`.

**Arrow colors in light theme:** Use hex colors matching the source layer (e.g., `#1e40af` for core links, `#0d9488` for agg links). Define separate SVG markers per color.

## Technical Implementation Details

### Component Rendering
Components are rounded rectangles (`rx="6"`) with 1.5px strokes. To prevent arrows from showing through semi-transparent fills, use a **double-rect masking technique**:
1. Draw an opaque background rect (`#0f172a`)
2. Draw the semi-transparent styled rect on top

### Connection Rules
- **Z-Order:** Draw arrows *early* in the SVG (after the grid) so they render behind component boxes
- **Arrowheads:** Defined via SVG markers
- **Security Flows:** Use dashed lines in rose color (`#fb7185`)
- **Boundaries:**
  - *Security Groups:* Dashed (`4,4`), rose color
  - *Regions:* Large dashed (`8,4`), amber color, `rx="12"`

### Spacing & Layout Logic
- **Standard Height:** 60px (Services); 80-120px (Large components)
- **Vertical Gap:** Minimum 40px between components
- **Message Buses:** Must be placed *in the gap* between services, not overlapping them
- **Legend Placement:** **CRITICAL.** Must be placed outside all boundary boxes. Calculate the lowest Y-coordinate of all boundaries and place the legend at least 20px below it.

## Document Structure

The generated HTML file follows a four-part layout:
1. **Header:** Title with a pulsing dot indicator and subtitle
2. **Main SVG:** The diagram contained within a rounded border card
3. **Summary Cards:** A grid of three cards below the diagram for high-level details
4. **Footer:** Minimal metadata

### Info Card Pattern
```html
<div class="card">
  <div class="card-header">
    <div class="card-dot cyan"></div>
    <h3>Title</h3>
  </div>
  <ul>
    <li>• Item one</li>
    <li>• Item two</li>
  </ul>
</div>
```

## Output Requirements
- **Single File:** One self-contained `.html` file
- **No External Dependencies:** All CSS and SVG must be inline (except Google Fonts)
- **No JavaScript:** Use pure CSS for any animations (like pulsing dots)
- **Compatibility:** Must render correctly in any modern web browser

## Network Topology Diagrams

For OT/IT network topology, distinguish between physical and logical diagrams:

### Physical Topology (设备物理拓扑)
**Purpose:** Show switch-level interconnects, port mappings, cable paths.
**Layout:** Vertical stack — Core → Aggregation → Access → Endpoints. Each switch is a box; lines connect ports.
**Content per switch box:** Hostname, model, management IP, uplink/downlink port labels, connected endpoint count.
**Endpoint boxes:** Interface name, remote device name/hostname, IP address, device type annotation.
**Connections:** Draw lines *before* boxes (Z-order). Label each line with local→remote interface names (e.g., `Te1/1/4→Te1/1/1`). Use different colors per layer.

For specific BI OT network naming conventions (LMJ, Core vs Aggregation vs Access prefixes, Stackwise Virtual pairs), and Cisco Command Runner CLI parsing patterns (CDP, LLDP, interface status extraction), see `references/bib-g144-topology.md` and `references/parsing-cisco-cli.md`.

### Logical Topology (逻辑拓扑)
**Purpose:** Show VLAN segmentation, IP subnets, device type categories, NAC/security posture, management plane.
**Layout:** Horizontal sections — Core bar → Aggregation bar → Access switch groups (separated by site/side) → VLAN tables → Endpoint categories → Security/NAC strip → Management strip.
**Key sections to include:**
1. **VLAN table:** List VLAN IDs, names, and which site they belong to. Use colored badge rectangles.
2. **IP plan:** Show subnet per VLAN.
3. **Device type breakdown:** Group endpoints by category (PLC, HMI, Thin Client, Panel, AP) with counts and IP ranges.
4. **NAC/Security strip:** Auth method, ISE servers, STP mode, DHCP snooping, UDLD status.
5. **Management strip:** VLAN ID, switch management IPs.
6. **Site comparison table** (for multi-site): Headers for each site, rows for VLANs / switch count / endpoint count.
7. **Issues/Findings box:** Unknown endpoints, auth failures, wrong VLAN placement, missing devices.

### OT Topology Data Sources
Typical Cisco IOS data sources and how to parse them:
- **CDP neighbors** (`show cdp neighbors detail`) → uplink/core peer discovery
- **LLDP neighbors** (`show lldp neighbors detail`) → endpoint discovery (PLCs, HMIs, Aruba APs with MAC-only sysName)
- **Interface status** (`show interfaces status`) → connected port census
- **Running config** (`show running-config`) → VLAN names, AAA servers, STP mode, hostname/model
- **Excel workbooks** (multi-sheet: Physical_Links, Endpoint_Links, Uplink_Links, Interface_Details, Summary_By_Device) → pre-parsed data, more reliable than raw CLI

**Parsing pattern:** Use Python `openpyxl` for Excel sources; for raw Command Runner `.txt` files, split by `==============Device : ...==============` markers, then regex-extract CDP/LLDP entries within each device section. See `references/ot-topology-parsing.md` for the full recipe.

## Template Reference

Load the full HTML template for the exact structure, CSS, and SVG component examples:

```
skill_view(name="architecture-diagram", file_path="templates/template.html")
```

For light-theme network topology examples, see:
```
skill_view(name="architecture-diagram", file_path="references/ot-topology-parsing.md")
```

The template contains working examples of every component type (frontend, backend, database, cloud, security), arrow styles (standard, dashed, curved), security groups, region boundaries, and the legend — use it as your structural reference when generating diagrams.
