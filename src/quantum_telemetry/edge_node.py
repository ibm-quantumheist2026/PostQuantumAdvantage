"""z3brameshOS Edge Node – QA11dSH platform orchestrator.

The :class:`EdgeNode` binds together:

* the DNA::}{::lang organism specification
* autonomous scientific discovery agents
* a digital-twin simulation pipeline
* energy-aware compute scheduling

It implements the system state transition model::

    S_{t+1} = O(S_t, A_t, P)

where *S* is the system state, *A* is the set of agent actions, and *P* is
the orchestration policy (expressed in terms of energy constraints and agent
coordination rules).

Supported runtime environments:

* Linux nodes
* Android / Termux devices
* browser-native (via WebAssembly bridge – runtime detection only)

Usage::

    from quantum_telemetry.edge_node import EdgeNode, build_default_node
    from quantum_telemetry.dna_lang import parse_organism

    spec = parse_organism(open("my_organism.dna").read())
    node = build_default_node(spec)
    node.start()
    result = node.run_experiment({"patient_id": "p001", "glucose": 5.4})
    print(node.status())
"""

from __future__ import annotations

import platform
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from quantum_telemetry.agents import (
    AgentStatus,
    CuratorAgent,
    DiscoveryAgent,
    OrchestratorAgent,
    SimulationAgent,
    VerifierAgent,
)
from quantum_telemetry.digital_twin import DigitalTwinPipeline, Domain, SimulationResult
from quantum_telemetry.dna_lang import OrganismSpec, MeshSpec
from quantum_telemetry.energy import EnergyAwareScheduler, EnergyMonitor, PowerLevel


# ---------------------------------------------------------------------------
# Runtime environment detection
# ---------------------------------------------------------------------------

def detect_runtime() -> str:
    """Detect the runtime environment.

    Returns one of ``"linux"``, ``"android"``, or ``"browser"``.
    """
    system = platform.system().lower()
    if "android" in system or "termux" in str(platform.version()).lower():
        return "android"
    if system == "linux":
        return "linux"
    return "browser"


# ---------------------------------------------------------------------------
# Node state
# ---------------------------------------------------------------------------

@dataclass
class NodeState:
    """Snapshot of edge-node state at time *t*.

    Attributes
    ----------
    state_id : str
        Unique identifier for this state snapshot.
    timestamp : float
        UNIX timestamp.
    runtime : str
        Detected runtime environment.
    active_agents : list[str]
        Names of agents currently in RUNNING state.
    mesh_connectivity : bool
        Whether the node is considered connected to the mesh.
    experiment_count : int
        Total experiments executed since node start.
    energy_summary : dict[str, Any]
        Latest energy metrics from the :class:`~energy.EnergyMonitor`.
    """

    state_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    runtime: str = "linux"
    active_agents: list[str] = field(default_factory=list)
    mesh_connectivity: bool = False
    experiment_count: int = 0
    energy_summary: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Edge node
# ---------------------------------------------------------------------------

class EdgeNode:
    """z3brameshOS edge node – QA11dSH platform runtime.

    Parameters
    ----------
    spec : OrganismSpec
        Parsed DNA::}{::lang organism specification.
    twin_domain : Domain
        Domain for the digital-twin pipeline.
    min_power_level : PowerLevel
        Minimum power level required to execute experiments.
    """

    def __init__(
        self,
        spec: OrganismSpec,
        twin_domain: Domain = Domain.GENERIC,
        min_power_level: PowerLevel = PowerLevel.MEDIUM,
    ) -> None:
        self.node_id = str(uuid.uuid4())
        self.spec = spec
        self.runtime = detect_runtime()
        self._started = False
        self._experiment_count = 0

        # Agent ensemble
        self._discovery = DiscoveryAgent()
        self._simulation = SimulationAgent()
        self._verifier = VerifierAgent()
        self._curator = CuratorAgent()
        self._orchestrator = OrchestratorAgent()
        self._orchestrator.register(self._discovery)
        self._orchestrator.register(self._simulation)
        self._orchestrator.register(self._verifier)
        self._orchestrator.register(self._curator)

        # Digital-twin pipeline
        self._twin = DigitalTwinPipeline(domain=twin_domain)

        # Energy management
        self._energy_monitor = EnergyMonitor()
        self._scheduler = EnergyAwareScheduler(self._energy_monitor, min_power_level)

        # Record initial energy state (idle node)
        self._energy_monitor.record(compute_load=0.05, energy_utilization=0.1)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the edge node and all managed agents."""
        self._discovery.start()
        self._simulation.start()
        self._verifier.start()
        self._curator.start()
        self._orchestrator.start()
        self._started = True

    def stop(self) -> None:
        """Stop all managed agents."""
        for agent in (
            self._discovery,
            self._simulation,
            self._verifier,
            self._curator,
            self._orchestrator,
        ):
            agent.stop()
        self._started = False

    # ------------------------------------------------------------------
    # Experiment execution
    # ------------------------------------------------------------------

    def update_energy(self, compute_load: float, energy_utilization: float) -> None:
        """Push a new energy reading to the monitor.

        Parameters
        ----------
        compute_load : float
            Fraction of compute in use (0.0 – 1.0).
        energy_utilization : float
            Fraction of power budget consumed (0.0 – 1.0).
        """
        self._energy_monitor.record(compute_load, energy_utilization)

    def run_experiment(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Run a full discovery + twin-simulation experiment.

        Internally executes both the agent collaboration loop
        (Hypothesis → Simulation → Validation → Knowledge) and the
        digital-twin pipeline (ingest → generate → simulate → optimize →
        feedback), subject to energy-aware scheduling.

        Parameters
        ----------
        input_data : dict
            Raw input data for both the discovery and twin pipelines.

        Returns
        -------
        dict
            Combined results from the agent loop and twin simulation.

        Raises
        ------
        RuntimeError
            If the node has not been started.
        """
        if not self._started:
            raise RuntimeError("EdgeNode must be started before running experiments.")

        # Energy-aware scheduling
        schedule_result = self._scheduler.schedule({"experiment": True})
        if not schedule_result["scheduled"]:
            return {
                "status": "deferred",
                "reason": "insufficient energy",
                "deferred_count": schedule_result["deferred_count"],
            }

        # Update energy to reflect active computation
        self._energy_monitor.record(compute_load=0.6, energy_utilization=0.4)

        # Run agent collaboration loop
        agent_results = self._orchestrator.run_discovery_loop(input_data)

        # Run digital-twin pipeline
        twin_result: SimulationResult = self._twin.run(input_data)

        self._experiment_count += 1

        # Return to lower energy state
        self._energy_monitor.record(compute_load=0.1, energy_utilization=0.15)

        return {
            "status": "completed",
            "experiment_id": str(uuid.uuid4()),
            "agent_loop": agent_results,
            "twin_simulation": {
                "run_id": twin_result.run_id,
                "model_id": twin_result.model_id,
                "outputs": twin_result.outputs,
                "elapsed_seconds": twin_result.elapsed_seconds,
            },
        }

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def status(self) -> NodeState:
        """Return the current node state snapshot."""
        active_agents = [
            a.name
            for a in (
                self._discovery,
                self._simulation,
                self._verifier,
                self._curator,
                self._orchestrator,
            )
            if a.status == AgentStatus.RUNNING
        ]
        return NodeState(
            runtime=self.runtime,
            active_agents=active_agents,
            mesh_connectivity=self._started,
            experiment_count=self._experiment_count,
            energy_summary=self._energy_monitor.summary(),
        )

    def console(self) -> str:
        """Render a text Terminal User Interface panel.

        Returns
        -------
        str
            A multi-line string resembling the z3braOS TUI layout described
            in the platform architecture.
        """
        s = self.status()
        agents_col = "\n".join(
            f"│ {a:<13} │" for a in (s.active_agents or ["(none)"])
        )
        energy = s.energy_summary
        lines = [
            "┌─────────────────────────────┐",
            "│ QA11dSH Edge Node Console   │",
            "├───────────────┬─────────────┤",
            "│ active agents │ tasks       │",
        ]
        tasks = ["run model", "check data", "update twin", "verify"]
        agent_names = s.active_agents or ["(none)"]
        rows = max(len(agent_names), len(tasks))
        for i in range(rows):
            a = agent_names[i] if i < len(agent_names) else ""
            t = tasks[i] if i < len(tasks) else ""
            lines.append(f"│ {a:<13} │ {t:<11} │")
        lines += [
            "├───────────────┴─────────────┤",
            "│ node metrics                │",
            f"│ compute load  {energy.get('current_load', 0.0):<13.2f} │",
            f"│ energy util.  {energy.get('current_utilization', 0.0):<13.2f} │",
            f"│ power level   {energy.get('current_power_level', 'n/a'):<13} │",
            f"│ mesh          {'connected' if s.mesh_connectivity else 'offline':<13} │",
            "└─────────────────────────────┘",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------

def build_default_node(
    spec: OrganismSpec | None = None,
    twin_domain: Domain = Domain.GENERIC,
) -> EdgeNode:
    """Build a ready-to-use edge node with sensible defaults.

    Parameters
    ----------
    spec : OrganismSpec | None
        Organism specification.  If ``None``, a default spec is used.
    twin_domain : Domain
        Domain for the digital-twin pipeline.

    Returns
    -------
    EdgeNode
        An unstarted :class:`EdgeNode` instance.
    """
    if spec is None:
        spec = OrganismSpec(
            name="QA11dSH",
            mesh=MeshSpec(name="z3braMesh", dimension=11),
            runtime_targets=["linux", "android", "browser"],
            agents=["discovery", "simulation", "verifier", "orchestrator"],
            domain="generic",
        )
    return EdgeNode(spec=spec, twin_domain=twin_domain)
