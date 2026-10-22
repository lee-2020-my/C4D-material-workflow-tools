# Changelog

## 0.1.0 - 2026-10-22

Initial open-source release.

### Added

- Redshift PBR material auto-link workflow.
- Folder-based PBR material creation.
- Automatic sRGB/Raw texture color-space handling.
- Material Tag Organizer cleanup/rebuild workflow.
- English and Chinese documentation.

### Fixed / hardened

- Skip missing material references safely in optimize-only mode.
- Connect Alpha/Opacity in the existing-material auto-link workflow.
- Connect Emission and enable emission weight in the existing-material auto-link workflow.
- Create batch-built materials explicitly in the Redshift node space.
- Guard Redshift IOR-port lookup against missing ports.
- Do not interpret Gloss/Glossiness as Roughness without inversion.
