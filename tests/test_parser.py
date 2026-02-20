"""Tests for quantum_telemetry.parser."""

import json
import os
import tempfile

import pytest

from quantum_telemetry.parser import (
    extract_execution_state,
    extract_measurements,
    parse_result,
)

SAMPLES_DIR = os.path.join(
    os.path.dirname(__file__), os.pardir, "samples"
)


# ---------------------------------------------------------------------------
# parse_result
# ---------------------------------------------------------------------------

class TestParseResult:
    def test_parse_from_dict(self):
        data = {"counts": {"00": 100, "11": 100}}
        assert parse_result(data) is data

    def test_parse_from_json_string(self):
        raw = '{"counts": {"00": 50}}'
        result = parse_result(raw)
        assert result == {"counts": {"00": 50}}

    def test_parse_from_file(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as fh:
            json.dump({"status": "COMPLETED"}, fh)
            path = fh.name
        try:
            result = parse_result(path)
            assert result["status"] == "COMPLETED"
        finally:
            os.unlink(path)

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_result("not json{{{")

    def test_non_dict_json_raises(self):
        with pytest.raises(ValueError, match="dictionary"):
            parse_result("[1, 2, 3]")


# ---------------------------------------------------------------------------
# extract_measurements
# ---------------------------------------------------------------------------

class TestExtractMeasurements:
    def test_legacy_format(self):
        result = parse_result(os.path.join(SAMPLES_DIR, "legacy_result.json"))
        counts = extract_measurements(result)
        assert counts == {"0x0": 2018, "0x3": 2078}

    def test_flat_counts_format(self):
        result = parse_result(
            os.path.join(SAMPLES_DIR, "flat_counts_result.json")
        )
        counts = extract_measurements(result)
        assert counts["000"] == 510
        assert sum(counts.values()) == 2048

    def test_sampler_v2_format(self):
        result = parse_result(
            os.path.join(SAMPLES_DIR, "sampler_v2_result.json")
        )
        counts = extract_measurements(result)
        assert "00" in counts
        assert "11" in counts
        assert abs(counts["00"] - 0.498) < 1e-6

    def test_missing_measurements_raises(self):
        with pytest.raises(KeyError, match="No measurement data found"):
            extract_measurements({"status": "COMPLETED"})


# ---------------------------------------------------------------------------
# extract_execution_state
# ---------------------------------------------------------------------------

class TestExtractExecutionState:
    def test_legacy_result(self):
        result = parse_result(os.path.join(SAMPLES_DIR, "legacy_result.json"))
        state = extract_execution_state(result)
        assert state["status"] == "COMPLETED"
        assert state["backend_name"] == "ibm_brisbane"
        assert state["shots"] == 4096
        assert state["success"] is True
        assert state["job_id"] == "ct4k8x7gqbc00080f5pg"

    def test_time_taken_maps_to_execution_time(self):
        result = {"status": "COMPLETED", "time_taken": 5.5}
        state = extract_execution_state(result)
        assert state["execution_time"] == 5.5

    def test_empty_result_returns_empty(self):
        state = extract_execution_state({})
        assert state == {}
