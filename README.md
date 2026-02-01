# ap-copy-master-to-blink

Copy master calibration frames from library to blink directories where light frames are located.

## Overview

`ap-copy-master-to-blink` prepares light frames for manual review (blinking) by copying their required master calibration frames from the calibration library to the blink directories. This ensures calibration frames are in place before lights are moved to the data directory.

**Note**: This tool is designed for the **darks library workflow** with cooled cameras where master darks are stored in a permanent library and reused across sessions. It is **not designed** for nightly darks workflows with uncooled cameras.

## Workflow Position

1. **ap-move-master-to-library** - Organizes masters into calibration library
2. **Manual blinking review** - Visual inspection and culling of lights
3. **ap-copy-master-to-blink** - **(THIS TOOL)** Copies masters to blink directories
4. **ap-move-light-to-data** - Moves lights to data when calibration complete

**Important**: Calibration frames are NOT needed for blinking. They are needed before blinked lights can be moved to data.

## Master Frame Matching

### Dark Frames

Priority matching (in order):

1. **Exact exposure match**: Same camera, gain, offset, settemp, readoutmode, and exposure time
2. **Shorter exposure + bias**: If no exact match, find the longest dark exposure < light exposure
   - **Requires matching bias**: Will not use shorter dark without bias
3. **No match**: If no exact dark and no bias, skip (logged as missing)

### Flat Frames

- Match by: camera, optic, filter, gain, offset, settemp, readoutmode, focallen
- **DATE must match exactly**: Current implementation requires exact date match
- Future enhancements planned for flexible date matching (see Limitations)

### Bias Frames

- Match by: camera, gain, offset, settemp, readoutmode
- **Only copied when needed**: When dark exposure < light exposure

## Installation

```bash
# From source
git clone https://github.com/jewzaam/ap-copy-master-to-blink.git
cd ap-copy-master-to-blink
make install

# Development installation
make install-dev
```

## Usage

```bash
# Basic usage
python -m ap_copy_master_to_blink <library_dir> <blink_dir>

# With dry-run (show what would be copied without copying)
python -m ap_copy_master_to_blink <library_dir> <blink_dir> --dry-run

# With debug output
python -m ap_copy_master_to_blink <library_dir> <blink_dir> --debug

# Real example
python -m ap_copy_master_to_blink \
    "F:/Astrophotography/_Calibration Library" \
    "F:/Astrophotography/RedCat51@f4.9+ASI2600MM/10_Blink"
```

### Arguments

- `library_dir`: Path to calibration library (supports env vars like `$VAR` or `${VAR}`)
- `blink_dir`: Path to blink directory tree (supports env vars)
- `--dry-run`: Show what would be copied without actually copying files
- `--debug`: Enable debug logging

## Directory Structure

### Expected Library Structure

```
library/
├── MASTER BIAS/
│   └── {camera}/
│       └── masterBias_GAIN_{gain}_OFFSET_{offset}_SETTEMP_{settemp}_READOUTM_{readoutmode}.xisf
│
├── MASTER DARK/
│   └── {camera}/
│       └── masterDark_EXPOSURE_{exposure}_GAIN_{gain}_OFFSET_{offset}_SETTEMP_{settemp}_READOUTM_{readoutmode}.xisf
│
└── MASTER FLAT/
    └── {camera}/
        └── {optic}/
            └── DATE_{YYYY-MM-DD}/
                └── masterFlat_FILTER_{filter}_GAIN_{gain}_OFFSET_{offset}_SETTEMP_{settemp}_FOCALLEN_{focallen}_READOUTM_{readoutmode}.xisf
```

### Blink Directory Structure

Masters are copied to the DATE directory (not scattered across filter subdirectories):

```
blink/
└── M31/
    └── DATE_2024-01-15/          # <-- ALL calibration frames HERE
        ├── masterDark_*.xisf
        ├── masterBias_*.xisf
        ├── masterFlat_FILTER_Ha_*.xisf
        ├── masterFlat_FILTER_OIII_*.xisf
        ├── masterFlat_FILTER_SII_*.xisf
        ├── FILTER_Ha/
        │   └── light_*.fits
        ├── FILTER_OIII/
        │   └── light_*.fits
        └── FILTER_SII/
            └── light_*.fits
```

**Rationale**: All calibration frames in one place (DATE directory) makes them easier to find and manage. Darks are shared across filter subdirectories since they're exposure-dependent, not filter-dependent.

## Current Limitations

### Exact DATE Matching for Flats

Current implementation requires flats to have exact DATE match with lights. Future enhancements planned:

- **Older flats**: Scan DATE subdirectories < light frame date and pick the most recent
- **Newer flats**: Scan DATE subdirectories > light frame date and pick the oldest
- **Date tolerance**: Configuration option for flat date tolerance (e.g., ±7 days)

See TODO comments in `matching.py:find_matching_flat()` for implementation notes.

## Development

```bash
# Install development dependencies
make install-dev

# Run tests
make test

# Run linting
make lint

# Format code
make format

# Check code formatting
make format-check

# Type checking
make typecheck

# Coverage
make coverage

# Run all checks (format, lint, typecheck, test, coverage)
make
```

## Testing

Tests cover:
- Configuration validation
- Dark/flat/bias matching logic
- File copying and directory scanning
- Edge cases (missing masters, date mismatches)

## Repository

GitHub: https://github.com/jewzaam/ap-copy-master-to-blink

## License

Apache License 2.0 - See LICENSE file for details.

Copyright 2024 jewzaam
