"""
Tests for flat batch selection logic in copy_masters.py.

Covers the batch flat date selection functions:
- _collect_filters_by_date
- _find_candidate_dates_with_all_filters
- _resolve_flat_for_date
"""

import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from ap_common.constants import (
    NORMALIZED_HEADER_CAMERA,
    NORMALIZED_HEADER_GAIN,
    NORMALIZED_HEADER_OFFSET,
    NORMALIZED_HEADER_SETTEMP,
    NORMALIZED_HEADER_READOUTMODE,
    NORMALIZED_HEADER_EXPOSURESECONDS,
    NORMALIZED_HEADER_FILTER,
    NORMALIZED_HEADER_DATE,
    NORMALIZED_HEADER_FILENAME,
    NORMALIZED_HEADER_OPTIC,
    NORMALIZED_HEADER_FOCALLEN,
)

from ap_copy_master_to_blink.copy_masters import (
    _collect_filters_by_date,
    _find_candidate_dates_with_all_filters,
    _resolve_flat_for_date,
)


class TestCollectFiltersByDate(unittest.TestCase):
    """Tests for _collect_filters_by_date function."""

    def _make_config_key(self, filter_name, date_str):
        """Helper to build a config key tuple."""
        return (
            "ASI2600MM",  # camera
            "100",  # gain
            "50",  # offset
            "-10",  # settemp
            "0",  # readoutmode
            "300",  # exposure
            filter_name,  # filter
            date_str,  # date
        )

    def test_single_date_single_filter(self):
        """Single group yields one date with one filter."""
        groups = {
            self._make_config_key("Ha", "2024-01-15"): [{"metadata": "light1"}],
        }

        result = _collect_filters_by_date(groups)

        self.assertEqual(result, {"2024-01-15": {"Ha"}})

    def test_single_date_multiple_filters(self):
        """Multiple groups on same date collect all filters."""
        groups = {
            self._make_config_key("Ha", "2024-01-15"): [{"m": "1"}],
            self._make_config_key("OIII", "2024-01-15"): [{"m": "2"}],
            self._make_config_key("SII", "2024-01-15"): [{"m": "3"}],
        }

        result = _collect_filters_by_date(groups)

        self.assertEqual(result, {"2024-01-15": {"Ha", "OIII", "SII"}})

    def test_multiple_dates(self):
        """Groups across multiple dates are separated correctly."""
        groups = {
            self._make_config_key("Ha", "2024-01-15"): [{"m": "1"}],
            self._make_config_key("OIII", "2024-01-15"): [{"m": "2"}],
            self._make_config_key("Ha", "2024-01-20"): [{"m": "3"}],
        }

        result = _collect_filters_by_date(groups)

        self.assertEqual(len(result), 2)
        self.assertEqual(result["2024-01-15"], {"Ha", "OIII"})
        self.assertEqual(result["2024-01-20"], {"Ha"})

    def test_empty_groups(self):
        """Empty groups dict returns empty result."""
        result = _collect_filters_by_date({})
        self.assertEqual(result, {})

    def test_skips_none_date(self):
        """Groups with None date are skipped."""
        groups = {
            self._make_config_key("Ha", None): [{"m": "1"}],
        }

        result = _collect_filters_by_date(groups)

        self.assertEqual(result, {})

    def test_skips_none_filter(self):
        """Groups with None filter are skipped."""
        groups = {
            self._make_config_key(None, "2024-01-15"): [{"m": "1"}],
        }

        result = _collect_filters_by_date(groups)

        self.assertEqual(result, {})

    def test_skips_malformed_config_key(self):
        """Groups with short config keys are skipped."""
        groups = {
            ("cam", "100"): [{"m": "1"}],  # Only 2 elements instead of 8
        }

        result = _collect_filters_by_date(groups)

        self.assertEqual(result, {})


class TestFindCandidateDatesWithAllFilters(unittest.TestCase):
    """Tests for _find_candidate_dates_with_all_filters function."""

    def setUp(self):
        """Set up test fixtures."""
        self.library_dir = Path("/test/library")
        self.light_metadata = {
            NORMALIZED_HEADER_CAMERA: "ASI2600MM",
            NORMALIZED_HEADER_GAIN: "100",
            NORMALIZED_HEADER_OFFSET: "50",
            NORMALIZED_HEADER_SETTEMP: "-10",
            NORMALIZED_HEADER_READOUTMODE: "0",
            NORMALIZED_HEADER_EXPOSURESECONDS: "300",
            NORMALIZED_HEADER_FILTER: "Ha",
            NORMALIZED_HEADER_DATE: "2024-01-15",
            NORMALIZED_HEADER_OPTIC: "RedCat51",
            NORMALIZED_HEADER_FOCALLEN: "250",
        }

    def test_empty_required_filters(self):
        """No required filters returns empty dict."""
        result = _find_candidate_dates_with_all_filters(
            self.library_dir, self.light_metadata, set(), None
        )
        self.assertEqual(result, {})

    @patch("ap_copy_master_to_blink.copy_masters.find_candidate_flat_dates")
    @patch("ap_copy_master_to_blink.copy_masters.find_flat_for_date")
    def test_single_filter_returns_all_dates(self, mock_find_flat, mock_candidates):
        """Single filter returns all candidate dates."""
        mock_candidates.return_value = {
            "2024-01-10": {NORMALIZED_HEADER_FILENAME: "/lib/flat_10.xisf"},
            "2024-01-20": {NORMALIZED_HEADER_FILENAME: "/lib/flat_20.xisf"},
        }
        mock_find_flat.return_value = {NORMALIZED_HEADER_FILENAME: "/lib/flat.xisf"}

        result = _find_candidate_dates_with_all_filters(
            self.library_dir, self.light_metadata, {"Ha"}, None
        )

        self.assertEqual(len(result), 2)
        self.assertIn("2024-01-10", result)
        self.assertIn("2024-01-20", result)

    @patch("ap_copy_master_to_blink.copy_masters.find_candidate_flat_dates")
    @patch("ap_copy_master_to_blink.copy_masters.find_flat_for_date")
    def test_multiple_filters_intersects_dates(self, mock_find_flat, mock_candidates):
        """Multiple filters only return dates that have ALL filters."""

        def mock_candidate_dates(library_dir, metadata, cutoff):
            filt = metadata.get(NORMALIZED_HEADER_FILTER)
            if filt == "Ha":
                return {
                    "2024-01-10": {NORMALIZED_HEADER_FILENAME: "/lib/ha_10.xisf"},
                    "2024-01-20": {NORMALIZED_HEADER_FILENAME: "/lib/ha_20.xisf"},
                }
            elif filt == "OIII":
                return {
                    "2024-01-10": {NORMALIZED_HEADER_FILENAME: "/lib/oiii_10.xisf"},
                    # Missing 2024-01-20 for OIII
                }
            return {}

        mock_candidates.side_effect = mock_candidate_dates
        mock_find_flat.return_value = {NORMALIZED_HEADER_FILENAME: "/lib/flat.xisf"}

        result = _find_candidate_dates_with_all_filters(
            self.library_dir, self.light_metadata, {"Ha", "OIII"}, None
        )

        # Only 2024-01-10 has both Ha and OIII
        self.assertEqual(len(result), 1)
        self.assertIn("2024-01-10", result)
        self.assertNotIn("2024-01-20", result)

    @patch("ap_copy_master_to_blink.copy_masters.find_candidate_flat_dates")
    def test_no_common_dates(self, mock_candidates):
        """No common dates across filters returns empty dict."""

        def mock_candidate_dates(library_dir, metadata, cutoff):
            filt = metadata.get(NORMALIZED_HEADER_FILTER)
            if filt == "Ha":
                return {
                    "2024-01-10": {NORMALIZED_HEADER_FILENAME: "/lib/ha_10.xisf"},
                }
            elif filt == "OIII":
                return {
                    "2024-01-20": {NORMALIZED_HEADER_FILENAME: "/lib/oiii_20.xisf"},
                }
            return {}

        mock_candidates.side_effect = mock_candidate_dates

        result = _find_candidate_dates_with_all_filters(
            self.library_dir, self.light_metadata, {"Ha", "OIII"}, None
        )

        self.assertEqual(result, {})

    @patch("ap_copy_master_to_blink.copy_masters.find_candidate_flat_dates")
    @patch("ap_copy_master_to_blink.copy_masters.find_flat_for_date")
    def test_cutoff_date_passed_through(self, mock_find_flat, mock_candidates):
        """Cutoff date is passed to find_candidate_flat_dates."""
        mock_candidates.return_value = {}

        _find_candidate_dates_with_all_filters(
            self.library_dir, self.light_metadata, {"Ha"}, "2024-01-05"
        )

        # Verify cutoff was passed
        call_args = mock_candidates.call_args
        self.assertEqual(call_args[0][2], "2024-01-05")

    @patch("ap_copy_master_to_blink.copy_masters.find_candidate_flat_dates")
    @patch("ap_copy_master_to_blink.copy_masters.find_flat_for_date")
    def test_modifies_filter_in_search_metadata(self, mock_find_flat, mock_candidates):
        """Each filter search uses modified metadata with that filter."""
        mock_candidates.return_value = {}

        _find_candidate_dates_with_all_filters(
            self.library_dir, self.light_metadata, {"G", "R"}, None
        )

        # Should have been called twice (once per filter)
        self.assertEqual(mock_candidates.call_count, 2)

        # Extract the filter values used in each call
        filters_used = set()
        for call in mock_candidates.call_args_list:
            metadata = call[0][1]
            filters_used.add(metadata[NORMALIZED_HEADER_FILTER])

        self.assertEqual(filters_used, {"G", "R"})


class TestResolveFlatForDate(unittest.TestCase):
    """Tests for _resolve_flat_for_date function."""

    def setUp(self):
        """Set up test fixtures."""
        self.library_dir = Path("/test/library")
        self.light_metadata = {
            NORMALIZED_HEADER_CAMERA: "ASI2600MM",
            NORMALIZED_HEADER_GAIN: "100",
            NORMALIZED_HEADER_OFFSET: "50",
            NORMALIZED_HEADER_SETTEMP: "-10",
            NORMALIZED_HEADER_READOUTMODE: "0",
            NORMALIZED_HEADER_EXPOSURESECONDS: "300",
            NORMALIZED_HEADER_FILTER: "Ha",
            NORMALIZED_HEADER_DATE: "2024-01-15",
            NORMALIZED_HEADER_OPTIC: "RedCat51",
            NORMALIZED_HEADER_FOCALLEN: "250",
        }
        self.blink_dir_str = "/blink"
        self.state = {}

    def test_quiet_mode_returns_none(self):
        """Quiet mode skips interactive selection."""
        result = _resolve_flat_for_date(
            self.library_dir,
            self.light_metadata,
            "2024-01-15",
            {"Ha"},
            self.blink_dir_str,
            self.state,
            quiet=True,
            picker_limit=5,
        )

        self.assertIsNone(result)

    @patch(
        "ap_copy_master_to_blink.copy_masters._find_candidate_dates_with_all_filters"
    )
    def test_no_candidates_returns_none(self, mock_find):
        """No candidate dates returns None."""
        mock_find.return_value = {}

        result = _resolve_flat_for_date(
            self.library_dir,
            self.light_metadata,
            "2024-01-15",
            {"Ha"},
            self.blink_dir_str,
            self.state,
            quiet=False,
            picker_limit=5,
        )

        self.assertIsNone(result)

    @patch(
        "ap_copy_master_to_blink.copy_masters._find_candidate_dates_with_all_filters"
    )
    @patch("ap_copy_master_to_blink.copy_masters.pick_flat_date")
    def test_user_selects_date(self, mock_pick, mock_find):
        """User selecting a date returns it and updates state."""
        mock_find.return_value = {
            "2024-01-10": {NORMALIZED_HEADER_FILENAME: "/lib/flat_10.xisf"},
        }
        mock_pick.return_value = date(2024, 1, 10)

        result = _resolve_flat_for_date(
            self.library_dir,
            self.light_metadata,
            "2024-01-15",
            {"Ha"},
            self.blink_dir_str,
            self.state,
            quiet=False,
            picker_limit=5,
        )

        self.assertEqual(result, "2024-01-10")
        # State should be updated with selected date
        self.assertEqual(self.state[self.blink_dir_str], "2024-01-10")

    @patch(
        "ap_copy_master_to_blink.copy_masters._find_candidate_dates_with_all_filters"
    )
    @patch("ap_copy_master_to_blink.copy_masters.pick_flat_date")
    def test_user_selects_rig_changed(self, mock_pick, mock_find):
        """User selecting 'rig changed' returns None and updates cutoff."""
        mock_find.return_value = {
            "2024-01-10": {NORMALIZED_HEADER_FILENAME: "/lib/flat_10.xisf"},
        }
        mock_pick.return_value = None  # User chose "rig changed"

        result = _resolve_flat_for_date(
            self.library_dir,
            self.light_metadata,
            "2024-01-15",
            {"Ha"},
            self.blink_dir_str,
            self.state,
            quiet=False,
            picker_limit=5,
        )

        self.assertIsNone(result)
        # State should be updated with light date as cutoff
        self.assertEqual(self.state[self.blink_dir_str], "2024-01-15")

    @patch(
        "ap_copy_master_to_blink.copy_masters._find_candidate_dates_with_all_filters"
    )
    def test_exact_date_excluded_from_candidates(self, mock_find):
        """The exact light date is removed from candidates."""
        # Only candidate is the exact date itself
        mock_find.return_value = {
            "2024-01-15": {NORMALIZED_HEADER_FILENAME: "/lib/flat_15.xisf"},
        }

        result = _resolve_flat_for_date(
            self.library_dir,
            self.light_metadata,
            "2024-01-15",
            {"Ha"},
            self.blink_dir_str,
            self.state,
            quiet=False,
            picker_limit=5,
        )

        # Should be None since the only candidate was the exact date
        self.assertIsNone(result)

    @patch(
        "ap_copy_master_to_blink.copy_masters._find_candidate_dates_with_all_filters"
    )
    @patch("ap_copy_master_to_blink.copy_masters.pick_flat_date")
    def test_candidates_split_into_older_and_newer(self, mock_pick, mock_find):
        """Candidates are correctly split into older and newer lists."""
        mock_find.return_value = {
            "2024-01-10": {NORMALIZED_HEADER_FILENAME: "/lib/flat_10.xisf"},
            "2024-01-12": {NORMALIZED_HEADER_FILENAME: "/lib/flat_12.xisf"},
            "2024-01-20": {NORMALIZED_HEADER_FILENAME: "/lib/flat_20.xisf"},
        }
        mock_pick.return_value = date(2024, 1, 10)

        _resolve_flat_for_date(
            self.library_dir,
            self.light_metadata,
            "2024-01-15",
            {"Ha"},
            self.blink_dir_str,
            self.state,
            quiet=False,
            picker_limit=5,
        )

        # Verify picker was called with correct older/newer split
        mock_pick.assert_called_once()
        call_args = mock_pick.call_args[0]
        older_dates = call_args[2]
        newer_dates = call_args[3]

        self.assertEqual(older_dates, [date(2024, 1, 10), date(2024, 1, 12)])
        self.assertEqual(newer_dates, [date(2024, 1, 20)])

    @patch(
        "ap_copy_master_to_blink.copy_masters._find_candidate_dates_with_all_filters"
    )
    @patch("ap_copy_master_to_blink.copy_masters.pick_flat_date")
    def test_picker_label_includes_all_filters(self, mock_pick, mock_find):
        """Picker is called with 'ALL (filter1, filter2)' label."""
        mock_find.return_value = {
            "2024-01-10": {NORMALIZED_HEADER_FILENAME: "/lib/flat_10.xisf"},
        }
        mock_pick.return_value = date(2024, 1, 10)

        _resolve_flat_for_date(
            self.library_dir,
            self.light_metadata,
            "2024-01-15",
            {"G", "R"},
            self.blink_dir_str,
            self.state,
            quiet=False,
            picker_limit=5,
        )

        # Verify the filter_name argument contains ALL and the filter names
        call_args = mock_pick.call_args[0]
        filter_label = call_args[1]
        self.assertTrue(filter_label.startswith("ALL ("))
        self.assertIn("G", filter_label)
        self.assertIn("R", filter_label)

    def test_invalid_light_date_returns_none(self):
        """Invalid light date string returns None."""
        mock_target = (
            "ap_copy_master_to_blink.copy_masters"
            "._find_candidate_dates_with_all_filters"
        )
        with patch(mock_target) as mock_find:
            mock_find.return_value = {
                "2024-01-10": {NORMALIZED_HEADER_FILENAME: "/lib/flat_10.xisf"},
            }

            result = _resolve_flat_for_date(
                self.library_dir,
                self.light_metadata,
                "not-a-date",
                {"Ha"},
                self.blink_dir_str,
                self.state,
                quiet=False,
                picker_limit=5,
            )

            self.assertIsNone(result)

    @patch(
        "ap_copy_master_to_blink.copy_masters._find_candidate_dates_with_all_filters"
    )
    @patch("ap_copy_master_to_blink.copy_masters.pick_flat_date")
    def test_picker_limit_passed_through(self, mock_pick, mock_find):
        """Picker limit is passed through to pick_flat_date."""
        mock_find.return_value = {
            "2024-01-10": {NORMALIZED_HEADER_FILENAME: "/lib/flat_10.xisf"},
        }
        mock_pick.return_value = date(2024, 1, 10)

        _resolve_flat_for_date(
            self.library_dir,
            self.light_metadata,
            "2024-01-15",
            {"Ha"},
            self.blink_dir_str,
            self.state,
            quiet=False,
            picker_limit=10,
        )

        call_kwargs = mock_pick.call_args[1]
        self.assertEqual(call_kwargs["picker_limit"], 10)

    @patch(
        "ap_copy_master_to_blink.copy_masters._find_candidate_dates_with_all_filters"
    )
    def test_state_cutoff_used_for_candidate_search(self, mock_find):
        """Existing state cutoff is passed to candidate search."""
        self.state[self.blink_dir_str] = "2024-01-05"
        mock_find.return_value = {}

        _resolve_flat_for_date(
            self.library_dir,
            self.light_metadata,
            "2024-01-15",
            {"Ha"},
            self.blink_dir_str,
            self.state,
            quiet=False,
            picker_limit=5,
        )

        # Verify cutoff was passed from state
        call_args = mock_find.call_args[0]
        cutoff = call_args[3]
        self.assertEqual(cutoff, "2024-01-05")


if __name__ == "__main__":
    unittest.main()
