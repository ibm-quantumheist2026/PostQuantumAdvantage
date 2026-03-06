"""Tests for quantum_telemetry.edge_node."""

import pytest

from quantum_telemetry.dna_lang import parse_organism
from quantum_telemetry.edge_node import EdgeNode, NodeState, build_default_node, detect_runtime
from quantum_telemetry.digital_twin import Domain


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


class TestDetectRuntime:
    def test_returns_string(self):
        rt = detect_runtime()
        assert isinstance(rt, str)
        assert rt in ("linux", "android", "browser")


class TestBuildDefaultNode:
    def test_returns_edge_node(self):
        node = build_default_node()
        assert isinstance(node, EdgeNode)

    def test_custom_spec(self):
        spec = parse_organism(SAMPLE_SPEC)
        node = build_default_node(spec)
        assert node.spec.name == "QA11dSH"

    def test_custom_domain(self):
        node = build_default_node(twin_domain=Domain.HEALTHCARE)
        assert node._twin.domain == Domain.HEALTHCARE


class TestEdgeNodeLifecycle:
    def test_not_started_raises_on_run(self):
        node = build_default_node()
        with pytest.raises(RuntimeError, match="started"):
            node.run_experiment({"x": 1.0})

    def test_start_and_stop(self):
        node = build_default_node()
        node.start()
        status = node.status()
        assert len(status.active_agents) > 0
        node.stop()
        status2 = node.status()
        assert len(status2.active_agents) == 0

    def test_mesh_connected_after_start(self):
        node = build_default_node()
        assert node.status().mesh_connectivity is False
        node.start()
        assert node.status().mesh_connectivity is True


class TestEdgeNodeExperiment:
    def setup_method(self):
        self.node = build_default_node()
        self.node.start()

    def test_run_experiment_returns_completed(self):
        result = self.node.run_experiment({"glucose": 5.4, "bp": 120.0})
        assert result["status"] == "completed"

    def test_experiment_increments_count(self):
        self.node.run_experiment({"x": 1})
        self.node.run_experiment({"x": 2})
        assert self.node.status().experiment_count == 2

    def test_result_has_agent_loop_and_twin(self):
        result = self.node.run_experiment({"val": 42.0})
        assert "agent_loop" in result
        assert "twin_simulation" in result

    def test_twin_simulation_has_run_id(self):
        result = self.node.run_experiment({"v": 1.0})
        assert "run_id" in result["twin_simulation"]

    def test_energy_deferred_when_low(self):
        # Drive energy to low state
        self.node.update_energy(compute_load=0.99, energy_utilization=0.99)
        result = self.node.run_experiment({"x": 1})
        assert result["status"] == "deferred"


class TestEdgeNodeConsole:
    def test_console_renders_string(self):
        node = build_default_node()
        node.start()
        console = node.console()
        assert isinstance(console, str)
        assert "QA11dSH Edge Node Console" in console

    def test_console_shows_agent_names(self):
        node = build_default_node()
        node.start()
        console = node.console()
        assert "discovery" in console

    def test_console_shows_mesh_connected(self):
        node = build_default_node()
        node.start()
        console = node.console()
        assert "connected" in console


class TestEdgeNodeStatus:
    def test_status_returns_node_state(self):
        node = build_default_node()
        state = node.status()
        assert isinstance(state, NodeState)
        assert "readings" in state.energy_summary
