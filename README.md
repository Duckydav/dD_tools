# dD Tools for Nuke

A personal collection of open-source tools to streamline the compositing workflow in Nuke.

**Author:** David Francois — VFX Compositor & Pipeline TD
**GitHub:** [github.com/Duckydav](https://github.com/Duckydav)
**LinkedIn:** [linkedin.com/in/davidfrancois](https://www.linkedin.com/in/davidfrancois/)

---

## Tools Included

### Layer Manager
A PySide2 panel for managing AOV (Arbitrary Output Variables) layers in multi-layer EXR files.
- Tree-based visualization of EXR layers
- Mute / Solo control with keyboard shortcuts
- Quick search and section filtering (Light, Mask, Tech, Utility)
- Live sync with Nuke scene changes
- LightGrade and GradeAOV integration

### LightGrade Gizmo
A Nuke gizmo for per-layer color grading of EXR AOVs.
- Integrates with Layer Manager
- Supports multiple light layer workflow

### Crypto Tool
Utilities for working with Cryptomatte nodes in Nuke.
- Smart layer name parsing and filtering
- Configurable exclude/singularize word lists

### Label Generator
Automated node labeling system with customizable templates.

### Label
Quick label tools for selected nodes.

### Shuffle Utilities
Helper functions for creating and managing Shuffle nodes from EXR layers.

### Mattes Inclusion
DIMATTE layer remapper — remaps matte layers onto a Read node for downstream use.

### Viewer Caller
Organizes and routes Viewer inputs for cleaner compositing setups.

---

## Requirements

- **Nuke**: 13.0+ (tested with 14.0)
- **Python**: 3.7+
- **PySide2**: 5.15.0+ (bundled with Nuke 13+)
- **OS**: Windows, macOS, Linux

---

## Installation

1. Copy the `dD_tools/` folder into your `.nuke` directory:

```
~/.nuke/dD_tools/
```

2. Copy `init.py` into your `.nuke` directory (or add the following line to your existing `~/.nuke/init.py`):

```python
nuke.pluginAddPath("dD_tools")
```

3. Restart Nuke. The **dD** menu will appear in the menu bar.

### Studio Installation

Deploy `dD_tools/` to a shared network location and add the path in your studio `init.py`:

```python
nuke.pluginAddPath(r"/path/to/shared/nuke/dD_tools")
```

For studio-specific integration (custom gizmo/toolset paths), edit `dD_tools/layer_manager/lm_config.py`:

```python
STUDIO_MODE      = True
STUDIO_GIZMO_DIR  = r"/your/studio/gizmos"
STUDIO_SCRIPT_DIR = r"/your/studio/toolsets"
```

---

## Attribution

If you use dD Tools in your work, a credit is appreciated:

**David Francois** — VFX Compositor & Pipeline TD
- GitHub: [github.com/Duckydav](https://github.com/Duckydav)
- LinkedIn: [linkedin.com/in/davidfrancois](https://www.linkedin.com/in/davidfrancois/)

A mention in your credits, on social media, or in your tool's README is very welcome.

---

## Support

If these tools save you time, consider buying me a coffee:
[buymeacoffee.com/ddavidfranc](https://buymeacoffee.com/ddavidfranc)

---

## License

MIT License — see [LICENSE](LICENSE) for details.

Free to use, modify, and distribute. Attribution appreciated but not required by the license.
