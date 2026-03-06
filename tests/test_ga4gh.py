"""Tests for quantum_telemetry.ga4gh – GA4GH VRS identifiers."""

from __future__ import annotations

import base64
import hashlib
import json

import pytest

from quantum_telemetry.ga4gh import annotate_result, compute_digest, compute_vrs_id


SAMPLE_COUNTS = {"00": 512, "11": 512}


# ---------------------------------------------------------------------------
# compute_digest
# ---------------------------------------------------------------------------

class TestComputeDigest:
    def test_returns_string(self):
        digest = compute_digest(SAMPLE_COUNTS)
        assert isinstance(digest, str)

    def test_length_is_32(self):
        # 24 bytes → ceil(24 * 8 / 6) = 32 base64url chars (no padding)
        digest = compute_digest(SAMPLE_COUNTS)
        assert len(digest) == 32

    def test_base64url_characters_only(self):
        digest = compute_digest(SAMPLE_COUNTS)
        valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
        assert all(c in valid_chars for c in digest)

    def test_no_padding(self):
        digest = compute_digest(SAMPLE_COUNTS)
        assert "=" not in digest

    def test_deterministic(self):
        assert compute_digest(SAMPLE_COUNTS) == compute_digest(SAMPLE_COUNTS)

    def test_key_order_invariant(self):
        a = {"00": 512, "11": 512}
        b = {"11": 512, "00": 512}
        assert compute_digest(a) == compute_digest(b)

    def test_different_data_differ(self):
        assert compute_digest({"00": 1}) != compute_digest({"00": 2})

    def test_matches_manual_computation(self):
        obj = {"00": 100, "11": 200}
        canonical = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
        raw = hashlib.sha512(canonical).digest()[:24]
        expected = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
        assert compute_digest(obj) == expected


# ---------------------------------------------------------------------------
# compute_vrs_id
# ---------------------------------------------------------------------------

class TestComputeVrsId:
    def test_default_prefix(self):
        vrs_id = compute_vrs_id(SAMPLE_COUNTS)
        assert vrs_id.startswith("ga4gh:QM.")

    def test_custom_prefix(self):
        vrs_id = compute_vrs_id(SAMPLE_COUNTS, type_prefix="VA")
        assert vrs_id.startswith("ga4gh:VA.")

    def test_digest_part_is_32_chars(self):
        vrs_id = compute_vrs_id(SAMPLE_COUNTS)
        prefix, digest = vrs_id.rsplit(".", 1)
        assert len(digest) == 32

    def test_id_field_excluded_from_digest(self):
        obj_with_id = dict(SAMPLE_COUNTS, id="some-existing-id")
        obj_without_id = dict(SAMPLE_COUNTS)
        assert compute_vrs_id(obj_with_id) == compute_vrs_id(obj_without_id)

    def test_ga4gh_id_field_excluded_from_digest(self):
        obj_with_ga4gh_id = dict(SAMPLE_COUNTS, ga4gh_id="ga4gh:QM.previous")
        obj_without = dict(SAMPLE_COUNTS)
        assert compute_vrs_id(obj_with_ga4gh_id) == compute_vrs_id(obj_without)

    def test_deterministic(self):
        assert compute_vrs_id(SAMPLE_COUNTS) == compute_vrs_id(SAMPLE_COUNTS)

    def test_different_counts_differ(self):
        assert compute_vrs_id({"00": 1, "11": 1}) != compute_vrs_id({"00": 2, "11": 2})


# ---------------------------------------------------------------------------
# annotate_result
# ---------------------------------------------------------------------------

class TestAnnotateResult:
    def test_adds_ga4gh_id_key(self):
        result = {"counts": {"00": 100, "11": 100}, "status": "COMPLETED"}
        annotated = annotate_result(result)
        assert "ga4gh_id" in annotated

    def test_original_not_mutated(self):
        result = {"counts": {"00": 100}, "status": "COMPLETED"}
        annotate_result(result)
        assert "ga4gh_id" not in result

    def test_id_starts_with_prefix(self):
        result = {"counts": {"00": 100}, "status": "COMPLETED"}
        annotated = annotate_result(result)
        assert annotated["ga4gh_id"].startswith("ga4gh:QM.")

    def test_custom_prefix_forwarded(self):
        result = {"counts": {"00": 100}}
        annotated = annotate_result(result, type_prefix="EX")
        assert annotated["ga4gh_id"].startswith("ga4gh:EX.")

    def test_stable_across_calls(self):
        result = {"counts": {"00": 500, "11": 500}, "shots": 1000}
        assert annotate_result(result)["ga4gh_id"] == annotate_result(result)["ga4gh_id"]

    def test_other_fields_preserved(self):
        result = {"counts": {"00": 100}, "status": "COMPLETED", "shots": 4096}
        annotated = annotate_result(result)
        assert annotated["status"] == "COMPLETED"
        assert annotated["shots"] == 4096
        assert annotated["counts"] == {"00": 100}
