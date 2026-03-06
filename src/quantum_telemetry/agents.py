"""Autonomous Scientific Discovery Agents for the QA11dSH platform.

Implements the five core agent types described in the platform architecture:

* **Discovery**   – hypothesis generation
* **Simulation**  – model testing
* **Verifier**    – statistical validation
* **Curator**     – knowledge integration
* **Orchestrator**– experiment planning and agent coordination

The agent collaboration loop follows the pattern::

    Hypothesis → Simulation → Validation → Knowledge
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    """Lifecycle state of an agent."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class AgentRole(str, Enum):
    """Functional roles for QA11dSH agents."""

    DISCOVERY = "discovery"
    SIMULATION = "simulation"
    VERIFIER = "verifier"
    CURATOR = "curator"
    ORCHESTRATOR = "orchestrator"


@dataclass
class AgentTask:
    """A unit of work dispatched to an agent."""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    completed: bool = False


class BaseAgent:
    """Base class for all QA11dSH platform agents.

    Parameters
    ----------
    name : str
        Human-readable agent name.
    role : AgentRole
        Functional role of this agent.
    """

    def __init__(self, name: str, role: AgentRole) -> None:
        self.agent_id: str = str(uuid.uuid4())
        self.name = name
        self.role = role
        self.status = AgentStatus.IDLE
        self._tasks: list[AgentTask] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Transition agent to RUNNING state."""
        self.status = AgentStatus.RUNNING

    def pause(self) -> None:
        """Transition agent to PAUSED state."""
        self.status = AgentStatus.PAUSED

    def stop(self) -> None:
        """Transition agent to STOPPED state."""
        self.status = AgentStatus.STOPPED

    # ------------------------------------------------------------------
    # Task management
    # ------------------------------------------------------------------

    def dispatch(self, task: AgentTask) -> AgentTask:
        """Accept a task and process it.

        Sub-classes override :meth:`_process` to implement domain logic.
        """
        self._tasks.append(task)
        task.result = self._process(task)
        task.completed = True
        return task

    def _process(self, task: AgentTask) -> dict[str, Any]:
        """Process a task and return a result dict. Override in subclasses."""
        return {"status": "ok", "agent": self.name}

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        """Return a summary of agent state."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role.value,
            "status": self.status.value,
            "tasks_completed": sum(1 for t in self._tasks if t.completed),
        }


# ---------------------------------------------------------------------------
# Concrete agent implementations
# ---------------------------------------------------------------------------


class DiscoveryAgent(BaseAgent):
    """Generates hypotheses from incoming data."""

    def __init__(self, name: str = "discovery") -> None:
        super().__init__(name, AgentRole.DISCOVERY)

    def _process(self, task: AgentTask) -> dict[str, Any]:
        data = task.payload.get("data", {})
        hypotheses = [
            f"hypothesis_{i}"
            for i in range(max(1, len(data)))
        ]
        return {"hypotheses": hypotheses, "source_keys": list(data.keys())}


class SimulationAgent(BaseAgent):
    """Tests models against hypotheses."""

    def __init__(self, name: str = "simulation") -> None:
        super().__init__(name, AgentRole.SIMULATION)

    def _process(self, task: AgentTask) -> dict[str, Any]:
        hypothesis = task.payload.get("hypothesis", "unknown")
        parameters = task.payload.get("parameters", {})
        score = sum(hash(k) % 100 for k in parameters) % 100 / 100.0
        return {
            "hypothesis": hypothesis,
            "simulation_score": score,
            "parameters_used": parameters,
        }


class VerifierAgent(BaseAgent):
    """Performs statistical validation of simulation results."""

    def __init__(self, name: str = "verifier") -> None:
        super().__init__(name, AgentRole.VERIFIER)

    def _process(self, task: AgentTask) -> dict[str, Any]:
        results = task.payload.get("results", [])
        if not results:
            return {"valid": False, "reason": "no results provided"}
        scores = [float(r) for r in results if isinstance(r, (int, float))]
        if not scores:
            return {"valid": False, "reason": "no numeric results"}
        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        return {
            "valid": True,
            "mean": mean,
            "variance": variance,
            "n_samples": len(scores),
        }


class CuratorAgent(BaseAgent):
    """Integrates validated findings into the knowledge graph."""

    def __init__(self, name: str = "curator") -> None:
        super().__init__(name, AgentRole.CURATOR)
        self._knowledge: list[dict[str, Any]] = []

    def _process(self, task: AgentTask) -> dict[str, Any]:
        finding = task.payload.get("finding", {})
        entry = {
            "timestamp": time.time(),
            "finding": finding,
            "entry_id": str(uuid.uuid4()),
        }
        self._knowledge.append(entry)
        return {"integrated": True, "entry_id": entry["entry_id"], "total_entries": len(self._knowledge)}

    @property
    def knowledge_base(self) -> list[dict[str, Any]]:
        """Return all integrated knowledge entries."""
        return list(self._knowledge)


class OrchestratorAgent(BaseAgent):
    """Plans experiments and coordinates the agent collaboration loop.

    The collaboration loop is::

        Hypothesis → Simulation → Validation → Knowledge
    """

    def __init__(self, name: str = "orchestrator") -> None:
        super().__init__(name, AgentRole.ORCHESTRATOR)
        self._managed_agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register an agent for orchestration."""
        self._managed_agents[agent.role.value] = agent

    def run_discovery_loop(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute one full Hypothesis→Simulation→Validation→Knowledge cycle.

        Parameters
        ----------
        input_data : dict
            Raw data passed to the discovery agent.

        Returns
        -------
        dict
            Consolidated results from the full cycle.
        """
        agents = self._managed_agents

        # Step 1: Discovery
        discovery: DiscoveryAgent = agents.get(AgentRole.DISCOVERY.value)  # type: ignore[assignment]
        hyp_task = AgentTask(name="generate_hypotheses", payload={"data": input_data})
        hyp_result = discovery.dispatch(hyp_task).result or {}

        # Step 2: Simulation (use first hypothesis)
        simulation: SimulationAgent = agents.get(AgentRole.SIMULATION.value)  # type: ignore[assignment]
        hypothesis = (hyp_result.get("hypotheses") or ["h0"])[0]
        sim_task = AgentTask(
            name="simulate_hypothesis",
            payload={"hypothesis": hypothesis, "parameters": input_data},
        )
        sim_result = simulation.dispatch(sim_task).result or {}

        # Step 3: Verification
        verifier: VerifierAgent = agents.get(AgentRole.VERIFIER.value)  # type: ignore[assignment]
        score = sim_result.get("simulation_score", 0.0)
        ver_task = AgentTask(
            name="verify_simulation",
            payload={"results": [score]},
        )
        ver_result = verifier.dispatch(ver_task).result or {}

        # Step 4: Curation
        curator: CuratorAgent = agents.get(AgentRole.CURATOR.value)  # type: ignore[assignment]
        cur_task = AgentTask(
            name="integrate_finding",
            payload={
                "finding": {
                    "hypothesis": hypothesis,
                    "simulation": sim_result,
                    "verification": ver_result,
                }
            },
        )
        cur_result = curator.dispatch(cur_task).result or {}

        return {
            "hypothesis": hypothesis,
            "simulation": sim_result,
            "verification": ver_result,
            "curation": cur_result,
        }

    def _process(self, task: AgentTask) -> dict[str, Any]:
        return {
            "managed_agents": list(self._managed_agents.keys()),
            "task": task.name,
        }
