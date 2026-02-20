"""Tests for quantum_telemetry.visualizer."""

import os
import tempfile

from quantum_telemetry.visualizer import plot_measurement_counts


class TestPlotMeasurementCounts:
    def test_saves_png_file(self):
        counts = {"00": 500, "11": 500}
        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "chart.png")
            plot_measurement_counts(counts, output_path=output)
            assert os.path.isfile(output)
            assert os.path.getsize(output) > 0

    def test_handles_single_bitstring(self):
        counts = {"0": 1024}
        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "single.png")
            plot_measurement_counts(counts, output_path=output)
            assert os.path.isfile(output)

    def test_custom_title(self):
        counts = {"00": 1, "01": 2, "10": 3, "11": 4}
        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "titled.png")
            plot_measurement_counts(
                counts, title="GHZ State", output_path=output
            )
            assert os.path.isfile(output)
