"""GA4GH Genomic Knowledge Standards – VRS v2.0-style computed identifiers.

Implements the GA4GH Variation Representation Specification (VRS) v2.0
digest algorithm for quantum measurement results, enabling globally unique,
registry-free identification of measurement states that is compatible with
the GA4GH machine-readable JSON-schema ecosystem (VRS, Cat-VRS, VA-Spec).

The digest algorithm follows the GA4GH standard:

1. Canonicalise the object to compact, sorted-key JSON (RFC 8785 subset).
2. Compute SHA-512.
3. Truncate to 24 bytes.
4. Encode as URL-safe base64 without padding.
5. Prefix with ``ga4gh:<TypeAbbrev>.``.

References
----------
* GA4GH VRS v2.0 – https://vrs.ga4gh.org/
* GA4GH GKS digest convention – https://w3id.org/ga4gh/schema/gks-common
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

# Number of bytes retained from the SHA-512 digest (matches the GA4GH spec).
_DIGEST_BYTES: int = 24


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _canonical_bytes(obj: Any) -> bytes:
    """Return a deterministic JSON serialisation of *obj* as UTF-8 bytes."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_digest(obj: Any) -> str:
    """Compute a GA4GH VRS v2.0-style digest for *obj*.

    The digest is the URL-safe base64 encoding (without ``=`` padding) of the
    first 24 bytes of ``SHA-512(canonical_json(obj))``.

    Parameters
    ----------
    obj : Any
        Any JSON-serialisable Python object.

    Returns
    -------
    str
        A 32-character base64url-encoded digest string.
    """
    raw = hashlib.sha512(_canonical_bytes(obj)).digest()[:_DIGEST_BYTES]
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def compute_vrs_id(obj: dict, type_prefix: str = "QM") -> str:
    """Compute a VRS-style globally unique identifier for a quantum result.

    The identifier follows the GA4GH ``ga4gh:<Type>.<digest>`` convention.
    Any existing ``"id"`` or ``"ga4gh_id"`` field in *obj* is excluded from
    the digest computation so that the identifier is stable.

    Parameters
    ----------
    obj : dict
        The object to identify (e.g. a measurement-counts dictionary or a
        full IBM Quantum result).
    type_prefix : str
        Short type abbreviation used in the identifier prefix.
        Defaults to ``"QM"`` (Quantum Measurement).

    Returns
    -------
    str
        A GA4GH-style identifier such as ``ga4gh:QM.<digest>``.
    """
    excluded = {"id", "ga4gh_id"}
    canonical = {k: v for k, v in obj.items() if k not in excluded}
    return f"ga4gh:{type_prefix}.{compute_digest(canonical)}"


def annotate_result(result: dict, type_prefix: str = "QM") -> dict:
    """Return a copy of *result* with a ``"ga4gh_id"`` field added.

    The ``"ga4gh_id"`` is computed by :func:`compute_vrs_id` and provides a
    stable, globally unique, registry-free identifier for the result payload.

    Parameters
    ----------
    result : dict
        An IBM Quantum result dictionary.
    type_prefix : str
        Short type abbreviation forwarded to :func:`compute_vrs_id`.

    Returns
    -------
    dict
        A shallow copy of *result* with the ``"ga4gh_id"`` key added.
    """
    annotated = dict(result)
    annotated["ga4gh_id"] = compute_vrs_id(result, type_prefix=type_prefix)
    return annotated
