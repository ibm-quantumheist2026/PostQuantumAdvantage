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

    def test_pqc_json_output(self, capsys):
        path = os.path.join(SAMPLES_DIR, "legacy_result.json")
        main([path, "--json", "--pqc"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "pcrb_hashes" in data
        hashes = data["pcrb_hashes"]
        assert set(hashes.keys()) == {"raw_counts", "shadow_moments", "chain_hash"}
        for value in hashes.values():
            assert len(value) == 64

    def test_pqc_human_readable_output(self, capsys):
        path = os.path.join(SAMPLES_DIR, "flat_counts_result.json")
        main([path, "--pqc"])
        captured = capsys.readouterr()
        assert "PCRB Hashes:" in captured.out

    def test_ga4gh_json_output(self, capsys):
        path = os.path.join(SAMPLES_DIR, "legacy_result.json")
        main([path, "--json", "--ga4gh"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "ga4gh_id" in data
        assert data["ga4gh_id"].startswith("ga4gh:QM.")

    def test_ga4gh_human_readable_output(self, capsys):
        path = os.path.join(SAMPLES_DIR, "flat_counts_result.json")
        main([path, "--ga4gh"])
        captured = capsys.readouterr()
        assert "GA4GH ID:" in captured.out

    def test_pqc_and_ga4gh_combined(self, capsys):
        path = os.path.join(SAMPLES_DIR, "sampler_v2_result.json")
        main([path, "--json", "--pqc", "--ga4gh"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "pcrb_hashes" in data
        assert "ga4gh_id" in data
