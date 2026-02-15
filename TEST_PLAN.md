# Test Plan

> This document describes the testing strategy for this project. It serves as the single source of truth for testing decisions and rationale.

## Overview

**Project:** ap-copy-master-to-blink
**Primary functionality:** Copy master calibration frames (darks, biases, flats) from a calibration library to blink directories based on light frame metadata matching.

## Testing Philosophy

This project follows the [ap-base Testing Standards](https://github.com/jewzaam/ap-base/blob/main/standards/standards/testing.md).

Key testing principles for this project:

- All calibration matching logic is tested with mocked ap_common utilities to verify correct parameters are passed (especially `profileFromPath=False` for library searches)
- Interactive components (flat date picker) are tested with mocked questionary to avoid TTY dependencies
- Output format and ordering are protected by explicit regression tests

## Test Categories

### Unit Tests

Tests for isolated functions with mocked dependencies.

| Module | Function | Test Coverage | Notes |
|--------|----------|---------------|-------|
| `config.py` | Constants | Verifies expected values and fields | Tests in `test_config.py` |
| `matching.py` | `find_matching_dark()` | Exact match, shorter exposure, no match, None filter handling | Mocks `find_darks_util` |
| `matching.py` | `find_matching_bias()` | Match found, no match, None values | Mocks `find_bias_util` |
| `matching.py` | `find_matching_flat()` | Match found, no match, None filter | Mocks `find_flats_util` |
| `matching.py` | `find_candidate_flat_dates()` | Multiple dates, cutoff filtering, deduplication, no-date entries | Mocks `find_flats_util` |
| `matching.py` | `find_flat_for_date()` | Different date search, no match, metadata not modified | Mocks `find_flats_util` |
| `matching.py` | `determine_required_masters()` | Exact dark, shorter dark with bias, shorter dark without bias | Mocks matching functions |
| `flat_state.py` | `load_state()` | Nonexistent file, empty file, valid state, invalid format, type coercion | Uses `tmp_path` |
| `flat_state.py` | `save_state()` | Roundtrip, parent directory creation, overwrite | Uses `tmp_path` |
| `flat_state.py` | `get_cutoff()` | Existing entry, missing entry, empty state | Pure logic |
| `flat_state.py` | `update_cutoff()` | New entry, advance, no regression, same date, multiple entries | Pure logic |
| `picker.py` | `_day_diff_label()` | Older singular/plural, newer singular/plural, same day | Pure logic |
| `picker.py` | `build_picker_items()` | Both older/newer, limit truncation, empty, overflow messages | Pure logic |
| `picker.py` | `pick_flat_date()` | No candidates, user selects none/older/newer, user cancels | Mocks `questionary.select` |
| `copy_masters.py` | `get_date_directory()` | From FILTER dir, from DATE dir, search upward | Pure logic |
| `copy_masters.py` | `scan_blink_directories()` | Returns metadata list | Mocks `get_filtered_metadata` |
| `copy_masters.py` | `group_lights_by_config()` | Multiple groups, None filter normalization, multiple None values | Pure logic |
| `copy_masters.py` | `copy_master_to_blink()` | New file, existing file, dry run | Mocks `copy_file` |
| `copy_masters.py` | `check_masters_exist()` | No directory, no files, dark/flat/all/partial exists | Mocks `Path.exists` |
| `copy_masters.py` | `_sort_groups_by_date()` | Ascending order, None date handling, preserves all groups | Pure logic |
| `copy_masters.py` | `_collect_filters_by_date()` | Single/multiple dates and filters, None values, malformed keys | Pure logic |
| `copy_masters.py` | `_find_candidate_dates_with_all_filters()` | Single/multiple filters, intersection, no common dates, cutoff | Mocks candidate search |
| `copy_masters.py` | `_resolve_flat_for_date()` | Quiet mode, no candidates, user selection, rig changed, date split | Mocks picker and candidates |
| `__main__.py` | `validate_directories()` | Both valid, missing/not-dir for library and blink | Mocks `Path.exists`/`is_dir` |
| `__main__.py` | `print_header()` | Output contains expected fields | Captures stdout |
| `__main__.py` | `print_summary()` | Output format, bias/dark/flat order | Captures stdout |
| `__main__.py` | `main()` | All CLI flags, error codes, missing masters | Mocks `process_blink_directory` |

### Integration Tests

Tests for multiple components working together.

| Workflow | Components | Test Coverage | Notes |
|----------|------------|---------------|-------|
| Multi-target copy | `process_blink_directory` + `copy_master_to_blink` | Masters copied to all target directories | Regression test |
| File path handling | `copy_master_to_blink` + `copy_file` | String paths passed to ap_common | Regression test |
| Library search | `find_matching_dark` + ap_common | `profileFromPath=False` verified | Regression test |
| Directory validation | `validate_directories` | Path objects required, not strings | Regression test |
| Flexible flat matching | `process_blink_directory` + state + picker | User selection, state updates, dry run, quiet mode | End-to-end with mocks |

## Untested Areas

| Area | Reason Not Tested |
|------|-------------------|
| ap_common library internals | Third-party library behavior; tested in ap-common project |
| FITS/XISF file I/O | Tested through ap_common; unit tests mock at the boundary |
| Real filesystem scanning | Integration with ap_common; tested via mocked `get_filtered_metadata` |
| questionary TTY interaction | External library; mocked in tests |

## Bug Fix Testing Protocol

All bug fixes to existing functionality **must** follow TDD:

1. Write a failing test that exposes the bug
2. Verify the test fails before implementing the fix
3. Implement the fix
4. Verify the test passes
5. Verify reverting the fix causes the test to fail again
6. Commit test and fix together with issue reference

### Regression Tests

| Issue | Test | Description |
|-------|------|-------------|
| profileFromPath regression | `TestLibraryProfileFromPath` | Verifies all library searches use `profileFromPath=False` |
| Output order regression | `TestPrintSummary` | Verifies bias/dark/flat output order is preserved |
| Multi-target copy | `test_copies_to_all_target_directories_in_group` | Masters copied to all target directories, not just first |
| String path handling | `test_copy_file_receives_strings_not_paths` | `copy_file` receives strings, not Path objects |
| Filename key | `test_process_blink_directory_uses_filename_key` | Uses `NORMALIZED_HEADER_FILENAME`, not `filepath` |

## Coverage Goals

**Target:** 80%+ line coverage

**Philosophy:** Coverage measures completeness, not quality. A test that executes code without meaningful assertions provides no value. Focus on:

- Testing behavior, not implementation details
- Covering edge cases and error conditions
- Ensuring assertions verify expected outcomes

## Running Tests

```bash
# Run all tests
make test

# Run with coverage
make coverage

# Run specific test
pytest tests/test_module.py::TestClass::test_function
```

## Test Data

Test data is:
- Generated programmatically in fixtures where possible
- Stored in `tests/fixtures/` when static files are needed
- Documented in `tests/fixtures/README.md`

**No Git LFS** - all test data must be small (< 100KB) or generated.

## Maintenance

When modifying this project:

1. **Adding features**: Add tests for new functionality after implementation
2. **Fixing bugs**: Follow TDD protocol above (test first, then fix)
3. **Refactoring**: Existing tests should pass without modification (behavior unchanged)
4. **Removing features**: Remove associated tests

## Changelog

| Date | Change | Rationale |
|------|--------|-----------|
| 2026-02-15 | Initial test plan | Document existing test suite covering 7 test files and 154 tests |
