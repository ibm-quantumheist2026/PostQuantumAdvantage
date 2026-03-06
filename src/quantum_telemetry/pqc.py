"""Post-quantum-resistant hash-chain integrity for PCRB records.

Implements the SHA-256-based hash chain described in ``pcrb_schema.json``.
SHA-256 provides 128-bit post-quantum collision resistance, making the
chain suitable for long-term data integrity in a harvest-now/decrypt-later
threat model.

The PCRB (Post-Quantum Cryptographic Record Bundle) schema defines three
hash fields per record:

* ``raw_counts``      – SHA-256 digest of the canonical measurement counts.
* ``shadow_moments``  – SHA-256 digest of the canonical shadow-moment data.
* ``chain_hash``      – SHA-256 digest of the concatenated previous two
                        digests, binding the bundle together.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _canonical_bytes(obj: Any) -> bytes:
    """Return a deterministic JSON serialisation of *obj* as UTF-8 bytes.

    Keys are sorted and the compact (no extra whitespace) representation is
    used so that the digest is independent of key ordering or formatting.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_counts_hash(counts: dict) -> str:
    """Compute the SHA-256 digest of canonical measurement *counts*.

    Parameters
    ----------
    counts : dict
        A mapping from bitstring to count (or probability), as returned by
        :func:`quantum_telemetry.parser.extract_measurements`.

    Returns
    -------
    str
        Lower-case hexadecimal SHA-256 digest.
    """
    return hashlib.sha256(_canonical_bytes(counts)).hexdigest()


def compute_shadow_moments_hash(moments: dict) -> str:
    """Compute the SHA-256 digest of canonical classical-shadow *moments*.

    Parameters
    ----------
    moments : dict
        A mapping of observable names to their estimated expectation values
        (e.g. ``{"F_tel": 0.92, "S_2_A": 1.08}``).

    Returns
    -------
    str
        Lower-case hexadecimal SHA-256 digest.
    """
    return hashlib.sha256(_canonical_bytes(moments)).hexdigest()


def compute_chain_hash(raw_counts_hash: str, shadow_moments_hash: str) -> str:
    """Compute the PCRB chain hash linking raw-counts and shadow-moments.

    The chain hash is the SHA-256 digest of the ASCII concatenation of the
    two input hex digests, providing a single tamper-evident binding of the
    complete record.

    Parameters
    ----------
    raw_counts_hash : str
        Hex digest produced by :func:`compute_counts_hash`.
    shadow_moments_hash : str
        Hex digest produced by :func:`compute_shadow_moments_hash`.

    Returns
    -------
    str
        Lower-case hexadecimal SHA-256 digest.
    """
    combined = (raw_counts_hash + shadow_moments_hash).encode("ascii")
    return hashlib.sha256(combined).hexdigest()


def compute_pcrb_hashes(counts: dict, moments: dict | None = None) -> dict[str, str]:
    """Compute all three PCRB hash fields for a measurement record.

    Parameters
    ----------
    counts : dict
        Measurement counts (bitstring → count).
    moments : dict | None
        Classical-shadow moments.  Defaults to an empty dict when *None*.

    Returns
    -------
    dict[str, str]
        A dictionary with keys ``"raw_counts"``, ``"shadow_moments"``,
        and ``"chain_hash"``, each containing a hex SHA-256 digest.
    """
    if moments is None:
        moments = {}
    raw_counts_hash = compute_counts_hash(counts)
    shadow_moments_hash = compute_shadow_moments_hash(moments)
    chain_hash = compute_chain_hash(raw_counts_hash, shadow_moments_hash)
    return {
        "raw_counts": raw_counts_hash,
        "shadow_moments": shadow_moments_hash,
        "chain_hash": chain_hash,
    }


def verify_pcrb_hashes(
    counts: dict,
    hashes: dict[str, str],
    moments: dict | None = None,
) -> bool:
    """Verify that *hashes* match the data in *counts* and *moments*.

    Parameters
    ----------
    counts : dict
        Measurement counts to verify against.
    hashes : dict[str, str]
        A PCRB hash bundle previously produced by :func:`compute_pcrb_hashes`.
    moments : dict | None
        Classical-shadow moments.  Defaults to an empty dict when *None*.

    Returns
    -------
    bool
        ``True`` if all three digests are consistent with the supplied data.
    """
    if not hashes:
        return False
    expected = compute_pcrb_hashes(counts, moments)
    return expected == hashes
