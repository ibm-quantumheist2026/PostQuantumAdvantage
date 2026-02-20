"""Tests for quantum_telemetry.cli."""

import json
import os
import tempfile

from quantum_telemetry.cli import main

SAMPLES_DIR = os.path.join(
    os.path.dirname(__file__), os.pardir, "samples"
)


class TestCLI:
    def test_json_output(self, capsys):
        path = os.path.join(SAMPLES_DIR, "legacy_result.json")
        main([path, "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "measurements" in data
        assert "execution_state" in data

    def test_human_readable_output(self, capsys):
        path = os.path.join(SAMPLES_DIR, "flat_counts_result.json")
        main([path])
        captured = capsys.readouterr()
        assert "Execution State:" in captured.out
        assert "Measurements:" in captured.out

    def test_output_chart(self):
        path = os.path.join(SAMPLES_DIR, "legacy_result.json")
        with tempfile.TemporaryDirectory() as tmpdir:
            chart_path = os.path.join(tmpdir, "out.png")
            main([path, "-o", chart_path, "--json"])
            assert os.path.isfile(chart_path)
