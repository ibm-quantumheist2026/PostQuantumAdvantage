"""Tests for quantum_telemetry.agents."""

import pytest

from quantum_telemetry.agents import (
    AgentRole,
    AgentStatus,
    AgentTask,
    CuratorAgent,
    DiscoveryAgent,
    OrchestratorAgent,
    SimulationAgent,
    VerifierAgent,
)


class TestBaseAgentLifecycle:
    def test_initial_status_is_idle(self):
        agent = DiscoveryAgent()
        assert agent.status == AgentStatus.IDLE

    def test_start_sets_running(self):
        agent = DiscoveryAgent()
        agent.start()
        assert agent.status == AgentStatus.RUNNING

    def test_pause_sets_paused(self):
        agent = DiscoveryAgent()
        agent.start()
        agent.pause()
        assert agent.status == AgentStatus.PAUSED

    def test_stop_sets_stopped(self):
        agent = DiscoveryAgent()
        agent.start()
        agent.stop()
        assert agent.status == AgentStatus.STOPPED

    def test_summary_contains_expected_keys(self):
        agent = DiscoveryAgent(name="test_discovery")
        summary = agent.summary()
        assert summary["name"] == "test_discovery"
        assert summary["role"] == AgentRole.DISCOVERY.value
        assert "status" in summary
        assert "tasks_completed" in summary


class TestDiscoveryAgent:
    def test_generates_hypotheses(self):
        agent = DiscoveryAgent()
        task = AgentTask(payload={"data": {"a": 1, "b": 2}})
        result = agent.dispatch(task).result
        assert "hypotheses" in result
        assert len(result["hypotheses"]) >= 1

    def test_task_marked_completed(self):
        agent = DiscoveryAgent()
        task = AgentTask(payload={"data": {}})
        agent.dispatch(task)
        assert task.completed is True


class TestSimulationAgent:
    def test_returns_simulation_score(self):
        agent = SimulationAgent()
        task = AgentTask(payload={"hypothesis": "h0", "parameters": {"x": 1}})
        result = agent.dispatch(task).result
        assert "simulation_score" in result
        assert 0.0 <= result["simulation_score"] <= 1.0

    def test_hypothesis_echoed_in_result(self):
        agent = SimulationAgent()
        task = AgentTask(payload={"hypothesis": "my_hypothesis", "parameters": {}})
        result = agent.dispatch(task).result
        assert result["hypothesis"] == "my_hypothesis"


class TestVerifierAgent:
    def test_validates_numeric_results(self):
        agent = VerifierAgent()
        task = AgentTask(payload={"results": [0.8, 0.9, 0.85]})
        result = agent.dispatch(task).result
        assert result["valid"] is True
        assert "mean" in result
        assert "variance" in result

    def test_empty_results_invalid(self):
        agent = VerifierAgent()
        task = AgentTask(payload={"results": []})
        result = agent.dispatch(task).result
        assert result["valid"] is False

    def test_non_numeric_results_invalid(self):
        agent = VerifierAgent()
        task = AgentTask(payload={"results": ["foo", "bar"]})
        result = agent.dispatch(task).result
        assert result["valid"] is False


class TestCuratorAgent:
    def test_integrates_finding(self):
        agent = CuratorAgent()
        task = AgentTask(payload={"finding": {"hypothesis": "h1", "score": 0.9}})
        result = agent.dispatch(task).result
        assert result["integrated"] is True
        assert "entry_id" in result

    def test_knowledge_base_grows(self):
        agent = CuratorAgent()
        for i in range(3):
            agent.dispatch(AgentTask(payload={"finding": {"i": i}}))
        assert len(agent.knowledge_base) == 3


class TestOrchestratorAgent:
    def _make_orchestrator(self):
        orch = OrchestratorAgent()
        orch.register(DiscoveryAgent())
        orch.register(SimulationAgent())
        orch.register(VerifierAgent())
        orch.register(CuratorAgent())
        return orch

    def test_run_discovery_loop_returns_all_stages(self):
        orch = self._make_orchestrator()
        result = orch.run_discovery_loop({"sensor_a": 1.5, "sensor_b": 2.3})
        assert "hypothesis" in result
        assert "simulation" in result
        assert "verification" in result
        assert "curation" in result

    def test_curator_receives_finding(self):
        orch = self._make_orchestrator()
        orch.run_discovery_loop({"x": 10})
        curator = orch._managed_agents[AgentRole.CURATOR.value]
        assert len(curator.knowledge_base) == 1
