"""Tests for quantum_telemetry.pqc – PCRB hash-chain integrity."""

from __future__ import annotations

import hashlib
import json

import pytest

from quantum_telemetry.pqc import (
    compute_chain_hash,
    compute_counts_hash,
    compute_pcrb_hashes,
    compute_shadow_moments_hash,
    verify_pcrb_hashes,
)


SAMPLE_COUNTS = {"00": 512, "01": 256, "10": 128, "11": 1152}
SAMPLE_MOMENTS = {"F_tel": 0.92, "S_2_A": 1.08, "J_nonrecip": 0.03}


# ---------------------------------------------------------------------------
# compute_counts_hash
# ---------------------------------------------------------------------------

class TestComputeCountsHash:
    def test_returns_hex_string(self):
        digest = compute_counts_hash(SAMPLE_COUNTS)
        assert isinstance(digest, str)
        assert len(digest) == 64  # SHA-256 produces 32 bytes → 64 hex chars

    def test_deterministic(self):
        assert compute_counts_hash(SAMPLE_COUNTS) == compute_counts_hash(SAMPLE_COUNTS)

    def test_key_order_invariant(self):
        counts_a = {"00": 100, "11": 200}
        counts_b = {"11": 200, "00": 100}
        assert compute_counts_hash(counts_a) == compute_counts_hash(counts_b)

    def test_different_counts_differ(self):
        assert compute_counts_hash({"00": 1}) != compute_counts_hash({"00": 2})

    def test_matches_manual_sha256(self):
        counts = {"00": 512, "11": 512}
        canonical = json.dumps(counts, sort_keys=True, separators=(",", ":")).encode()
        expected = hashlib.sha256(canonical).hexdigest()
        assert compute_counts_hash(counts) == expected

    def test_empty_counts(self):
        digest = compute_counts_hash({})
        assert len(digest) == 64


# ---------------------------------------------------------------------------
# compute_shadow_moments_hash
# ---------------------------------------------------------------------------

class TestComputeShadowMomentsHash:
    def test_returns_hex_string(self):
        digest = compute_shadow_moments_hash(SAMPLE_MOMENTS)
        assert len(digest) == 64

    def test_deterministic(self):
        assert (
            compute_shadow_moments_hash(SAMPLE_MOMENTS)
            == compute_shadow_moments_hash(SAMPLE_MOMENTS)
        )

    def test_different_moments_differ(self):
        assert compute_shadow_moments_hash({"F_tel": 0.9}) != compute_shadow_moments_hash(
            {"F_tel": 0.8}
        )

    def test_empty_moments(self):
        digest = compute_shadow_moments_hash({})
        assert len(digest) == 64


# ---------------------------------------------------------------------------
# compute_chain_hash
# ---------------------------------------------------------------------------

class TestComputeChainHash:
    def test_returns_hex_string(self):
        h1 = compute_counts_hash(SAMPLE_COUNTS)
        h2 = compute_shadow_moments_hash(SAMPLE_MOMENTS)
        chain = compute_chain_hash(h1, h2)
        assert len(chain) == 64

    def test_deterministic(self):
        h1 = "a" * 64
        h2 = "b" * 64
        assert compute_chain_hash(h1, h2) == compute_chain_hash(h1, h2)

    def test_order_matters(self):
        h1 = "a" * 64
        h2 = "b" * 64
        assert compute_chain_hash(h1, h2) != compute_chain_hash(h2, h1)

    def test_matches_manual_sha256(self):
        h1 = "deadbeef" * 8  # 64 hex chars
        h2 = "cafebabe" * 8
        combined = (h1 + h2).encode("ascii")
        expected = hashlib.sha256(combined).hexdigest()
        assert compute_chain_hash(h1, h2) == expected


# ---------------------------------------------------------------------------
# compute_pcrb_hashes
# ---------------------------------------------------------------------------

class TestComputePcrbHashes:
    def test_returns_three_keys(self):
        hashes = compute_pcrb_hashes(SAMPLE_COUNTS, SAMPLE_MOMENTS)
        assert set(hashes.keys()) == {"raw_counts", "shadow_moments", "chain_hash"}

    def test_all_values_are_64_char_hex(self):
        hashes = compute_pcrb_hashes(SAMPLE_COUNTS, SAMPLE_MOMENTS)
        for key, value in hashes.items():
            assert len(value) == 64, f"key={key!r} has unexpected length"

    def test_defaults_moments_to_empty_dict(self):
        hashes_explicit = compute_pcrb_hashes(SAMPLE_COUNTS, {})
        hashes_default = compute_pcrb_hashes(SAMPLE_COUNTS)
        assert hashes_explicit == hashes_default

    def test_chain_links_other_hashes(self):
        hashes = compute_pcrb_hashes(SAMPLE_COUNTS, SAMPLE_MOMENTS)
        expected_chain = compute_chain_hash(hashes["raw_counts"], hashes["shadow_moments"])
        assert hashes["chain_hash"] == expected_chain

    def test_deterministic(self):
        assert compute_pcrb_hashes(SAMPLE_COUNTS, SAMPLE_MOMENTS) == compute_pcrb_hashes(
            SAMPLE_COUNTS, SAMPLE_MOMENTS
        )


# ---------------------------------------------------------------------------
# verify_pcrb_hashes
# ---------------------------------------------------------------------------

class TestVerifyPcrbHashes:
    def test_valid_hashes_return_true(self):
        hashes = compute_pcrb_hashes(SAMPLE_COUNTS, SAMPLE_MOMENTS)
        assert verify_pcrb_hashes(SAMPLE_COUNTS, hashes, SAMPLE_MOMENTS) is True

    def test_valid_hashes_no_moments(self):
        hashes = compute_pcrb_hashes(SAMPLE_COUNTS)
        assert verify_pcrb_hashes(SAMPLE_COUNTS, hashes) is True

    def test_tampered_counts_return_false(self):
        hashes = compute_pcrb_hashes(SAMPLE_COUNTS, SAMPLE_MOMENTS)
        tampered = dict(SAMPLE_COUNTS)
        tampered["00"] += 1
        assert verify_pcrb_hashes(tampered, hashes, SAMPLE_MOMENTS) is False

    def test_tampered_moments_return_false(self):
        hashes = compute_pcrb_hashes(SAMPLE_COUNTS, SAMPLE_MOMENTS)
        tampered = dict(SAMPLE_MOMENTS)
        tampered["F_tel"] = 0.0
        assert verify_pcrb_hashes(SAMPLE_COUNTS, hashes, tampered) is False

    def test_tampered_chain_hash_returns_false(self):
        hashes = compute_pcrb_hashes(SAMPLE_COUNTS, SAMPLE_MOMENTS)
        corrupted = dict(hashes)
        corrupted["chain_hash"] = "0" * 64
        assert verify_pcrb_hashes(SAMPLE_COUNTS, corrupted, SAMPLE_MOMENTS) is False

    def test_empty_hashes_return_false(self):
        assert verify_pcrb_hashes(SAMPLE_COUNTS, {}) is False
