# C4D Material Workflow Tools

Open-source **Cinema 4D Python utilities** for repetitive material workflows, with a focus on Redshift PBR setup and material-tag cleanup for imported production assets.

[Latest release: v1.0.0](https://github.com/lee-2020-my/C4D-material-workflow-tools/releases/tag/v1.0.0) · [简体中文](README.zh-CN.md) · [MIT License](LICENSE)

## Quick download

**You do not need to download the whole repository.** Choose the tool you want:

| Download | Best for |
|---|---|
| [**Redshift PBR Material Builder v1.0.0**](https://github.com/lee-2020-my/C4D-material-workflow-tools/releases/download/v1.0.0/Redshift-PBR-Material-Builder-v1.0.0.zip) | Automatically building and connecting Redshift PBR materials |
| [**Material Tag Organizer v1.0.0**](https://github.com/lee-2020-my/C4D-material-workflow-tools/releases/download/v1.0.0/Material-Tag-Organizer-v1.0.0.zip) | Cleaning and reorganizing Cinema 4D material/selection tags; works with native C4D materials and Redshift materials |
| [**All tools v1.0.0**](https://github.com/lee-2020-my/C4D-material-workflow-tools/releases/download/v1.0.0/C4D-Material-Workflow-Tools-v1.0.0.zip) | Installing both tools |

## Installation

1. Download one of the ZIP files above and extract it.
2. Put the extracted plugin folder in a location such as `D:\C4D_Plugins\`.
3. In Cinema 4D, open **Preferences > Plugins** and add `D:\C4D_Plugins\` to the plugin search paths.
4. Restart Cinema 4D. The installed tool will appear under **Extensions**.

> **Redshift PBR Material Builder** requires Redshift. **Material Tag Organizer** works at Cinema 4D's material/tag level and is not limited to Redshift.

## Included tools

| Tool | What it does |
|---|---|
| **Redshift PBR Material Builder** | Detects common PBR texture channels, sets appropriate Redshift color spaces, builds/connects a Redshift material graph, and can batch-create materials from texture folders. |
| **Material Tag Organizer** | Cleans material/selection tags, merges duplicate materials by normalized name, sorts materials, standardizes names, and rebuilds polygon-selection/material-tag assignments. Works with native Cinema 4D materials as well as Redshift materials. |

These tools were built around practical Cinema 4D production workflows and are released as a small, standalone open-source toolkit.

## 1. Redshift PBR Material Builder

### Main features

- Detects Base Color / Albedo / Diffuse, AO, Roughness, Metalness, Normal / Bump, Displacement / Height, Opacity / Alpha and Emission from filenames.
- Sets **sRGB** for color/emission textures and **Raw** for data textures.
- Connects textures to a Redshift Standard Material.
- Adds helper nodes for AO, roughness, bump/normal and displacement workflows.
- Can scan a folder and batch-build materials when at least three recognized channel types are found for a texture set.
- Can rename the material from the detected texture-set name.
- Can assign the generated material to the active object and enable Redshift subdivision/displacement when displacement is present.

### Auto-connect an existing material

1. Create a **Redshift Standard Material**.
2. Add your PBR texture nodes to the material graph.
3. Make the material active in Cinema 4D.
4. Open **Extensions > Redshift PBR Material Builder** and run the auto-connect action.

The plugin scans texture sampler nodes, classifies them by filename, applies color-space settings and creates the required connections.

### Batch-create from a folder

1. Put one or more PBR texture sets in a folder.
2. Open **Extensions > Redshift PBR Material Builder**.
3. Choose the folder import action.
4. Select the texture folder. The plugin groups recognized texture sets and creates Redshift materials automatically.

Example filenames:

```text
Wood_BaseColor.png
Wood_Roughness.png
Wood_Normal.png
Wood_Metalness.png
Wood_AO.png
Wood_Displacement.exr
```

`Gloss`/`Glossiness` maps are intentionally **not** treated as Roughness automatically because they require inversion.

## 2. Material Tag Organizer

Designed for imported characters, vehicles and other assets that can arrive with many material channels, selection tags and inconsistent names.

The organizer works at Cinema 4D's material/tag level and is **not limited to Redshift**. It can organize tags that reference native/standard Cinema 4D materials as well as Redshift materials.

### Main features

- Processes multiple selected polygon objects.
- Removes invalid or orphaned selection/material tags when cleanup is enabled.
- Removes SDS/session-style tags handled by the current workflow.
- Merges materials that share the same normalized base name.
- Sorts document materials alphabetically.
- Standardizes material names with an `M_` prefix and safe characters.
- Rebuilds local material assignments using predictable selection names such as `00_M_CarPaint_Set`.
- Shows a summary after processing.

### Use

1. Open a copy of the scene you want to clean up.
2. Select one or more polygon objects.
3. Open **Extensions > Material Tag Organizer**.
4. Choose the cleanup/merge/organization options you need and run the tool.

> **Backup recommended:** cleanup operations can modify material tags, polygon selections and material assignments.

### Important limitation

Duplicate-material merging is currently **name-based**, not shader-graph-based. If different materials intentionally use names such as `Paint`, `Paint.1` and `Paint.2`, review the scene before running merge/organize on production data.

## Compatibility

The tools use Cinema 4D's Python API; the PBR builder additionally uses Redshift/Maxon node APIs. API identifiers can change between Cinema 4D/Redshift releases, so compatibility may vary by version.

The command plugin IDs included here are the IDs used by the author's current local workflow. If you redistribute a modified build as a separately registered Cinema 4D plugin, use an appropriate unique plugin ID.

## Roadmap

- Better UDIM handling.
- Configurable filename/channel presets.
- Optional Glossiness-to-Roughness inversion.
- More defensive Redshift version compatibility checks.
- Non-destructive/dry-run preview for material-tag cleanup.
- Additional validation before name-based material merging.

## Contributing

Bug reports, compatibility notes and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).

## Disclaimer

Cinema 4D, Redshift and related product names are trademarks of their respective owners. This project is independent and is not affiliated with or endorsed by Maxon.
