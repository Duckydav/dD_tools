# Layer Manager v2.40

Open source Nuke panel for AOV (Arbitrary Output Variables) layer management.

## Overview

**Layer Manager** is a PySide2-based Nuke panel that provides:
- Tree-based visualization of multi-layer EXR files
- Mute/Solo layer control with keyboard shortcuts
- Quick search and filtering by section (Light, Mask, Tech, Utility, Custom)
- Live sync with Nuke scene changes
- LightGrade integration for per-layer color corrections
- GradeAOV support (open source, Nukepedia)

## Requirements

- **Nuke**: 13.0+ (tested with 14.0+)
- **Python**: 3.7+
- **PySide2**: 5.15.0+
- **OS**: Windows, macOS, Linux

## Installation (User)

Copy the `layer_manager/` folder into your `.nuke` directory:

```
C:\Users\{username}\.nuke\layermanager\
```

Add to your `~/.nuke/menu.py`:
```python
import layermanager
```

## Installation (Studio)

Deploy the folder to a shared location, for example:

```
{Disk}:\{project}\pipeline_utils\lighting\nuke\tools\layermanager\
```

Add the path in your studio `init.py`:
```python
nuke.pluginAddPath(r"{Disk}:\{project}\pipeline_utils\lighting\nuke\tools\layermanager")
```

## Directory Structure

```
layermanager/
  __init__.py              # Package entry point
  layer_manager.py         # Main interface
  lm_config.py             # Central configuration
  prefs_manager.py         # JSON preferences manager
  lm_prefs_default.json    # Default preferences
  lightgrade_module.py     # LightGrade system
  shuffle.py               # Shuffle operations
  debug_help.py            # Help utilities
  utils_fonctions.py       # Shared utilities
  icons/                   # UI icons
```

## Usage

### Launch
- Via menu: **Tools > Layer Manager**
- Via Python: `import layermanager.layer_manager as lm; lm.run()`

### Keyboard Shortcuts (inside panel)
| Key | Action |
|-----|--------|
| H | Create Shuffle2 |
| G | Create LightGrade (Light section) |
| A | Add layer to LightGrade (Light section) |
| L | Create GradeAOV (Light section) |
| O | Create Roto |
| P | Create Cryptomatte |

### Preferences
Click the Settings icon to open the preferences dialog. Keywords, section
visibility, and refresh mode can all be configured and are saved to
`lm_prefs.json` (auto-generated, not committed to git).

## Known Issues

- EXR files with deep data may load slowly on first access
- GradeAOV requires the gizmo to be installed separately (Nukepedia or NST)

## Author

- **Author**: David Francois
- **GitHub**: [github.com/Duckydav](https://github.com/Duckydav)

## License

MIT License

---

**Version**: 2.40
**Repository**: [github.com/Duckydav/layer-manager](https://github.com/Duckydav/layer-manager)
