"""Parser for IBM Quantum telemetry JSON results.

Extracts Qiskit Primitive measurements and execution states from the JSON
payloads returned by IBM Quantum hardware.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def parse_result(source: str | Path | dict) -> dict:
    """Load an IBM Quantum result from a file path, JSON string, or dict.

    Parameters
    ----------
    source : str | Path | dict
        A file path to a JSON file, a raw JSON string, or an already-parsed
        dictionary.

    Returns
    -------
    dict
        The parsed result dictionary.

    Raises
    ------
    ValueError
        If *source* cannot be interpreted as valid JSON.
    FileNotFoundError
        If *source* is a path that does not exist.
    """
    if isinstance(source, dict):
        return source

    path = Path(source)
    if path.is_file():
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)

    # Try interpreting source as a raw JSON string.
    try:
        result = json.loads(source)
        if not isinstance(result, dict):
            raise ValueError("JSON must decode to a dictionary, got " + type(result).__name__)
        return result
    except json.JSONDecodeError as exc:
        raise ValueError(f"Cannot parse source as JSON: {exc}") from exc


def extract_measurements(result: dict) -> dict[str, int]:
    """Extract measurement counts from an IBM Quantum result.

    Supports several common payload layouts:
    * ``result["results"][i]["data"]["counts"]`` (legacy Qiskit format)
    * ``result["quasi_dists"]`` (Sampler V2 quasi-distributions)
    * ``result["counts"]`` (flat format)

    Parameters
    ----------
    result : dict
        A parsed IBM Quantum JSON result (see :func:`parse_result`).

    Returns
    -------
    dict[str, int]
        A mapping from bitstring to count.

    Raises
    ------
    KeyError
        If no recognisable measurement data is found.
    """
    # Legacy Qiskit result format
    if "results" in result:
        counts: dict[str, int] = {}
        for entry in result["results"]:
            entry_counts = (
                entry.get("data", {}).get("counts")
                or entry.get("counts")
                or {}
            )
            for bitstring, count in entry_counts.items():
                counts[bitstring] = counts.get(bitstring, 0) + int(count)
        if counts:
            return counts

    # Flat counts
    if "counts" in result:
        return {k: int(v) for k, v in result["counts"].items()}

    # Sampler quasi-distributions
    if "quasi_dists" in result:
        combined: dict[str, float] = {}
        for dist in result["quasi_dists"]:
            for bitstring, prob in dist.items():
                combined[bitstring] = combined.get(bitstring, 0.0) + prob
        return {k: v for k, v in combined.items()}

    raise KeyError(
        "No measurement data found. Expected one of: "
        "'results[].data.counts', 'counts', or 'quasi_dists'."
    )


def extract_execution_state(result: dict) -> dict[str, Any]:
    """Extract execution metadata from an IBM Quantum result.

    Pulls together status, timing, backend, and shot information from
    the various places they can appear in the payload.

    Parameters
    ----------
    result : dict
        A parsed IBM Quantum JSON result.

    Returns
    -------
    dict[str, Any]
        A dictionary with the following optional keys:
        ``status``, ``backend_name``, ``shots``, ``date``,
        ``execution_time``, ``job_id``, ``success``.
    """
    state: dict[str, Any] = {}

    # Top-level fields
    for key in ("status", "success", "job_id", "date", "backend_name"):
        if key in result:
            state[key] = result[key]

    # Nested under "metadata" or "header"
    for container_key in ("metadata", "header"):
        container = result.get(container_key, {})
        if isinstance(container, dict):
            for key in ("backend_name", "shots", "execution_time"):
                if key in container and key not in state:
                    state[key] = container[key]

    # Shots may also appear at top level
    if "shots" in result and "shots" not in state:
        state["shots"] = result["shots"]

    # Timing from "time_taken"
    if "time_taken" in result and "execution_time" not in state:
        state["execution_time"] = result["time_taken"]

    return state
