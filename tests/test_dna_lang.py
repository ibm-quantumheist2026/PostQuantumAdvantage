"""Tests for quantum_telemetry.dna_lang."""

import pytest

from quantum_telemetry.dna_lang import MeshSpec, OrganismSpec, parse_organism, render_organism


SAMPLE_SPEC = """
organism QA11dSH {
  mesh z3braMesh dimension=11
  runtime targets = [linux, android, browser]
  agents {
      discovery
      simulation
      verifier
      orchestrator
  }
  domain healthcare_digital_twin
}
"""


class TestParseOrganism:
    def test_parses_name(self):
        spec = parse_organism(SAMPLE_SPEC)
        assert spec.name == "QA11dSH"

    def test_parses_mesh(self):
        spec = parse_organism(SAMPLE_SPEC)
        assert spec.mesh.name == "z3braMesh"
        assert spec.mesh.dimension == 11

    def test_parses_runtime_targets(self):
        spec = parse_organism(SAMPLE_SPEC)
        assert "linux" in spec.runtime_targets
        assert "android" in spec.runtime_targets
        assert "browser" in spec.runtime_targets

    def test_parses_agents(self):
        spec = parse_organism(SAMPLE_SPEC)
        assert "discovery" in spec.agents
        assert "simulation" in spec.agents
        assert "verifier" in spec.agents
        assert "orchestrator" in spec.agents

    def test_parses_domain(self):
        spec = parse_organism(SAMPLE_SPEC)
        assert spec.domain == "healthcare_digital_twin"

    def test_missing_organism_keyword_raises(self):
        with pytest.raises(ValueError, match="organism"):
            parse_organism("mesh z3braMesh dimension=11")

    def test_parses_invariants(self):
        spec_with_invariants = SAMPLE_SPEC.replace(
            "domain healthcare_digital_twin",
            "domain healthcare_digital_twin\n  invariant energy_balanced\n  invariant sandbox_enforced",
        )
        spec = parse_organism(spec_with_invariants)
        assert "energy_balanced" in spec.invariants
        assert "sandbox_enforced" in spec.invariants

    def test_default_mesh_dimension(self):
        minimal = "organism Minimal { mesh myMesh }"
        spec = parse_organism(minimal)
        assert spec.mesh.dimension == 11  # default

    def test_no_agents_block(self):
        minimal = "organism Minimal { domain test }"
        spec = parse_organism(minimal)
        assert spec.agents == []


class TestRenderOrganism:
    def test_roundtrip(self):
        original = parse_organism(SAMPLE_SPEC)
        rendered = render_organism(original)
        reparsed = parse_organism(rendered)
        assert reparsed.name == original.name
        assert reparsed.mesh.dimension == original.mesh.dimension
        assert set(reparsed.runtime_targets) == set(original.runtime_targets)
        assert set(reparsed.agents) == set(original.agents)
        assert reparsed.domain == original.domain

    def test_rendered_contains_organism_keyword(self):
        spec = OrganismSpec(name="TestOrg")
        rendered = render_organism(spec)
        assert "organism TestOrg" in rendered

    def test_rendered_contains_mesh(self):
        spec = OrganismSpec(name="T", mesh=MeshSpec(name="myMesh", dimension=7))
        rendered = render_organism(spec)
        assert "myMesh" in rendered
        assert "dimension=7" in rendered
