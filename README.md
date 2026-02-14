# ap-copy-master-to-blink

[![Test](https://github.com/jewzaam/ap-copy-master-to-blink/actions/workflows/test.yml/badge.svg)](https://github.com/jewzaam/ap-copy-master-to-blink/actions/workflows/test.yml)
[![Coverage](https://github.com/jewzaam/ap-copy-master-to-blink/actions/workflows/coverage.yml/badge.svg)](https://github.com/jewzaam/ap-copy-master-to-blink/actions/workflows/coverage.yml)
[![Lint](https://github.com/jewzaam/ap-copy-master-to-blink/actions/workflows/lint.yml/badge.svg)](https://github.com/jewzaam/ap-copy-master-to-blink/actions/workflows/lint.yml)
[![Format](https://github.com/jewzaam/ap-copy-master-to-blink/actions/workflows/format.yml/badge.svg)](https://github.com/jewzaam/ap-copy-master-to-blink/actions/workflows/format.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

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

### Library Search Behavior

Library searches read **actual FITS headers** from calibration files, not path structure.

**Why this matters**:
- Library directories use bare equipment names (e.g., `ATR585M/SQA55`) without KEY_VALUE encoding
- Unlike blink directories (`{optic}@f{ratio}+{camera}`), library paths don't encode all metadata
- Files are searched with `profileFromPath=False` to ensure camera, optic, filter, gain, offset, etc. come from FITS headers
- Path-based metadata (like `DATE_2026-02-07`) still overrides file headers where present

**Technical detail**: This uses the `profileFromPath=False` parameter when calling `ap_common` calibration utilities. See regression tests in `tests/test_matching.py::TestLibraryProfileFromPath` for implementation details.

### Dark Frames

Priority matching (in order):

1. **Exact exposure match**: Same camera, gain, offset, settemp, readoutmode, and exposure time
2. **Shorter exposure + bias** (requires `--allow-bias`): If no exact match, find the longest dark exposure < light exposure
   - **Requires matching bias**: Will not use shorter dark without bias
   - **Default behavior**: Without `--allow-bias`, only exact exposure match darks are copied
3. **No match**: If no exact dark and no bias (or `--allow-bias` not specified), skip (logged as missing)

**Note**: By default, only exact exposure match darks are copied. Use `--allow-bias` to enable shorter dark + bias frame matching.

### Flat Frames

- Match by: camera, optic, filter, gain, offset, settemp, readoutmode, focallen
- **DATE must match exactly**: Current implementation requires exact date match
- Future enhancements planned for flexible date matching (see Limitations)

### Bias Frames

- Match by: camera, gain, offset, settemp, readoutmode
- **Only copied when needed**: When dark exposure < light exposure

## Installation

### From Git

```bash
pip install git+https://github.com/jewzaam/ap-copy-master-to-blink.git
```

### Development

```bash
git clone https://github.com/jewzaam/ap-copy-master-to-blink.git
cd ap-copy-master-to-blink
make install-dev
```

## Usage

```bash
# Basic usage
python -m ap_copy_master_to_blink <library_dir> <blink_dir>

# With dry-run (show what would be copied without copying)
python -m ap_copy_master_to_blink <library_dir> <blink_dir> --dryrun

# With debug output
python -m ap_copy_master_to_blink <library_dir> <blink_dir> --debug

# With quiet mode (minimal output)
python -m ap_copy_master_to_blink <library_dir> <blink_dir> --quiet

# Allow shorter darks with bias frames
python -m ap_copy_master_to_blink <library_dir> <blink_dir> --allow-bias

# Real example
python -m ap_copy_master_to_blink \
    "F:/Astrophotography/_Calibration Library" \
    "F:/Astrophotography/RedCat51@f4.9+ASI2600MM/10_Blink"
```

### Arguments

- `library_dir`: Path to calibration library (supports env vars like `$VAR` or `${VAR}`)
- `blink_dir`: Path to blink directory tree (supports env vars)
- `--dryrun`: Show what would be copied without actually copying files
- `--debug`: Enable debug logging
- `--quiet`, `-q`: Suppress progress output
- `--allow-bias`: Allow shorter darks with bias frames (default: only exact exposure match darks)

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

## Documentation

This tool is part of the astrophotography pipeline. For comprehensive documentation including workflow guides and integration with other tools, see:

- [Pipeline Overview](https://github.com/jewzaam/ap-base/blob/main/docs/index.md) - Full pipeline documentation
- [Workflow Guide](https://github.com/jewzaam/ap-base/blob/main/docs/workflow.md) - Detailed workflow with diagrams
- [ap-copy-master-to-blink Reference](https://github.com/jewzaam/ap-base/blob/main/docs/tools/ap-copy-master-to-blink.md) - API reference for this tool

## Repository

GitHub: https://github.com/jewzaam/ap-copy-master-to-blink

## License

Apache License 2.0 - See LICENSE file for details.

Copyright 2024 jewzaam
