"""
Tests for flat state file management.
"""

import unittest
import tempfile
from pathlib import Path

from ap_copy_master_to_blink.flat_state import (
    load_state,
    save_state,
    get_cutoff,
    update_cutoff,
)


class TestLoadState(unittest.TestCase):
    """Tests for load_state function."""

    def test_load_nonexistent_file(self):
        """Loading a nonexistent file returns empty dict."""
        result = load_state(Path("/nonexistent/state.yaml"))
        self.assertEqual(result, {})

    def test_load_empty_file(self):
        """Loading an empty file returns empty dict."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()
            result = load_state(Path(f.name))
        self.assertEqual(result, {})

    def test_load_valid_state(self):
        """Loading a valid YAML state file returns correct dict."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write('"/data/blink1": "2025-09-01"\n')
            f.write('"/data/blink2": "2025-08-15"\n')
            f.flush()
            result = load_state(Path(f.name))

        self.assertEqual(len(result), 2)
        self.assertEqual(result["/data/blink1"], "2025-09-01")
        self.assertEqual(result["/data/blink2"], "2025-08-15")

    def test_load_invalid_format(self):
        """Loading a file with non-dict content returns empty dict."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("- item1\n- item2\n")
            f.flush()
            result = load_state(Path(f.name))
        self.assertEqual(result, {})

    def test_load_values_converted_to_strings(self):
        """Values are converted to strings."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            # YAML may parse dates as date objects
            f.write("/data/blink: 2025-09-01\n")
            f.flush()
            result = load_state(Path(f.name))

        # Value should be string regardless of YAML parsing
        for value in result.values():
            self.assertIsInstance(value, str)


class TestSaveState(unittest.TestCase):
    """Tests for save_state function."""

    def test_save_and_load_roundtrip(self):
        """State can be saved and loaded back correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.yaml"
            state = {
                "/data/blink1": "2025-09-01",
                "/data/blink2": "2025-08-15",
            }
            save_state(state_path, state)
            loaded = load_state(state_path)

        self.assertEqual(loaded["/data/blink1"], "2025-09-01")
        self.assertEqual(loaded["/data/blink2"], "2025-08-15")

    def test_save_creates_parent_directories(self):
        """save_state creates parent directories if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "subdir" / "deep" / "state.yaml"
            save_state(state_path, {"key": "value"})
            self.assertTrue(state_path.exists())

    def test_save_empty_state(self):
        """Saving empty dict creates a valid YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.yaml"
            save_state(state_path, {})
            loaded = load_state(state_path)
        self.assertEqual(loaded, {})

    def test_save_overwrites_existing(self):
        """Saving overwrites existing state file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.yaml"
            save_state(state_path, {"old": "data"})
            save_state(state_path, {"new": "data"})
            loaded = load_state(state_path)

        self.assertNotIn("old", loaded)
        self.assertEqual(loaded["new"], "data")


class TestGetCutoff(unittest.TestCase):
    """Tests for get_cutoff function."""

    def test_get_existing_cutoff(self):
        """Getting cutoff for known blink dir returns the date."""
        state = {"/data/blink": "2025-09-01"}
        result = get_cutoff(state, "/data/blink")
        self.assertEqual(result, "2025-09-01")

    def test_get_missing_cutoff(self):
        """Getting cutoff for unknown blink dir returns None."""
        state = {"/data/blink": "2025-09-01"}
        result = get_cutoff(state, "/data/other")
        self.assertIsNone(result)

    def test_get_cutoff_empty_state(self):
        """Getting cutoff from empty state returns None."""
        result = get_cutoff({}, "/data/blink")
        self.assertIsNone(result)


class TestUpdateCutoff(unittest.TestCase):
    """Tests for update_cutoff function."""

    def test_update_new_entry(self):
        """Updating cutoff for new blink dir creates entry."""
        state = {}
        update_cutoff(state, "/data/blink", "2025-09-01")
        self.assertEqual(state["/data/blink"], "2025-09-01")

    def test_update_advances_cutoff(self):
        """Updating with newer date advances the cutoff."""
        state = {"/data/blink": "2025-08-01"}
        update_cutoff(state, "/data/blink", "2025-09-01")
        self.assertEqual(state["/data/blink"], "2025-09-01")

    def test_update_does_not_regress_cutoff(self):
        """Updating with older date does NOT regress the cutoff."""
        state = {"/data/blink": "2025-09-01"}
        update_cutoff(state, "/data/blink", "2025-08-01")
        self.assertEqual(state["/data/blink"], "2025-09-01")

    def test_update_same_date(self):
        """Updating with same date is a no-op (stays same)."""
        state = {"/data/blink": "2025-09-01"}
        update_cutoff(state, "/data/blink", "2025-09-01")
        self.assertEqual(state["/data/blink"], "2025-09-01")

    def test_update_multiple_entries(self):
        """Updating one entry doesn't affect others."""
        state = {
            "/data/blink1": "2025-08-01",
            "/data/blink2": "2025-07-01",
        }
        update_cutoff(state, "/data/blink1", "2025-09-01")
        self.assertEqual(state["/data/blink1"], "2025-09-01")
        self.assertEqual(state["/data/blink2"], "2025-07-01")


if __name__ == "__main__":
    unittest.main()
