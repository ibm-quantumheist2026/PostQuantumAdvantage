"""Command-line interface for quantum-telemetry."""

from __future__ import annotations

import argparse
import json
import sys

from quantum_telemetry.parser import (
    extract_execution_state,
    extract_measurements,
    parse_result,
)
from quantum_telemetry.visualizer import plot_measurement_counts


def main(argv: list[str] | None = None) -> None:
    """Entry point for the ``quantum-telemetry`` CLI."""
    parser = argparse.ArgumentParser(
        description="Parse and visualize IBM Quantum telemetry JSON results.",
    )
    parser.add_argument(
        "input",
        help="Path to an IBM Quantum JSON result file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Save the measurement bar chart to this file path.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Print extracted data as JSON to stdout.",
    )
    args = parser.parse_args(argv)

    result = parse_result(args.input)
    measurements = extract_measurements(result)
    execution_state = extract_execution_state(result)

    if args.json_output:
        json.dump(
            {"measurements": measurements, "execution_state": execution_state},
            sys.stdout,
            indent=2,
        )
        print()  # trailing newline
    else:
        print("Execution State:")
        for key, value in execution_state.items():
            print(f"  {key}: {value}")
        print()
        print("Measurements:")
        for bitstring, count in sorted(measurements.items()):
            print(f"  {bitstring}: {count}")

    if args.output:
        plot_measurement_counts(measurements, output_path=args.output)
        print(f"\nChart saved to {args.output}")
