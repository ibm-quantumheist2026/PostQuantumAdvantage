"""Energy-aware compute allocation for the QA11dSH platform.

The platform prioritises efficient and sustainable computation through:

* workload scheduling based on energy availability
* opportunistic compute
* low-power device participation
* hardware-accelerated workloads

The :class:`EnergyMonitor` tracks node energy state and the
:class:`EnergyAwareScheduler` decides whether to run a workload immediately
or defer it until conditions improve.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PowerLevel(str, Enum):
    """Coarse-grained node power state."""

    LOW = "low"       # < 20% capacity available
    MEDIUM = "medium" # 20 to 70% capacity available
    HIGH = "high"     # > 70% capacity available


@dataclass
class EnergyState:
    """Snapshot of a node's energy metrics.

    Attributes
    ----------
    timestamp : float
        UNIX timestamp of the reading.
    compute_load : float
        Fraction of CPU / compute capacity in use (0.0 – 1.0).
    energy_utilization : float
        Fraction of power budget consumed (0.0 – 1.0).
    available_capacity : float
        Estimated fraction of headroom remaining (0.0 – 1.0).
    power_level : PowerLevel
        Derived coarse-grained power level.
    contributes_to_grid : bool
        ``True`` when the node has surplus energy to export.
    """

    timestamp: float = field(default_factory=time.time)
    compute_load: float = 0.0
    energy_utilization: float = 0.0
    available_capacity: float = 1.0
    power_level: PowerLevel = PowerLevel.HIGH
    contributes_to_grid: bool = False

    @classmethod
    def from_metrics(cls, compute_load: float, energy_utilization: float) -> "EnergyState":
        """Construct an :class:`EnergyState` from raw metrics.

        Parameters
        ----------
        compute_load : float
            Fraction of compute in use (clamped to [0, 1]).
        energy_utilization : float
            Fraction of power budget consumed (clamped to [0, 1]).

        Returns
        -------
        EnergyState
        """
        compute_load = max(0.0, min(1.0, compute_load))
        energy_utilization = max(0.0, min(1.0, energy_utilization))
        available = max(0.0, 1.0 - energy_utilization)

        if available > 0.7:
            level = PowerLevel.HIGH
        elif available > 0.2:
            level = PowerLevel.MEDIUM
        else:
            level = PowerLevel.LOW

        contributes = available > 0.8 and compute_load < 0.2

        return cls(
            compute_load=compute_load,
            energy_utilization=energy_utilization,
            available_capacity=available,
            power_level=level,
            contributes_to_grid=contributes,
        )


class EnergyMonitor:
    """Tracks energy state history for an edge node.

    Parameters
    ----------
    history_limit : int
        Maximum number of readings to retain in memory.
    """

    def __init__(self, history_limit: int = 100) -> None:
        self._history: list[EnergyState] = []
        self._limit = history_limit

    def record(self, compute_load: float, energy_utilization: float) -> EnergyState:
        """Record a new energy snapshot.

        Parameters
        ----------
        compute_load : float
            Fraction of compute in use (0.0 – 1.0).
        energy_utilization : float
            Fraction of power budget consumed (0.0 – 1.0).

        Returns
        -------
        EnergyState
            The newly created snapshot.
        """
        state = EnergyState.from_metrics(compute_load, energy_utilization)
        self._history.append(state)
        if len(self._history) > self._limit:
            self._history.pop(0)
        return state

    @property
    def current(self) -> EnergyState | None:
        """Most recent energy state, or ``None`` if no readings exist."""
        return self._history[-1] if self._history else None

    @property
    def history(self) -> list[EnergyState]:
        """All recorded energy snapshots (oldest first)."""
        return list(self._history)

    def average_utilization(self) -> float:
        """Compute the mean energy utilization across all recorded readings."""
        if not self._history:
            return 0.0
        return sum(s.energy_utilization for s in self._history) / len(self._history)

    def summary(self) -> dict[str, Any]:
        """Return a human-readable summary dict."""
        cur = self.current
        return {
            "readings": len(self._history),
            "current_power_level": cur.power_level.value if cur else None,
            "current_load": cur.compute_load if cur else None,
            "current_utilization": cur.energy_utilization if cur else None,
            "average_utilization": self.average_utilization(),
            "contributes_to_grid": cur.contributes_to_grid if cur else False,
        }


class EnergyAwareScheduler:
    """Decides whether to run a workload based on current energy conditions.

    Parameters
    ----------
    monitor : EnergyMonitor
        The energy monitor to consult.
    min_power_level : PowerLevel
        Minimum power level required to schedule a workload immediately.
    """

    def __init__(
        self,
        monitor: EnergyMonitor,
        min_power_level: PowerLevel = PowerLevel.MEDIUM,
    ) -> None:
        self._monitor = monitor
        self._min_level = min_power_level
        self._deferred: list[dict[str, Any]] = []

    def can_schedule(self) -> bool:
        """Return ``True`` if current energy conditions permit scheduling."""
        cur = self._monitor.current
        if cur is None:
            return True  # no data → optimistically allow
        levels = [PowerLevel.LOW, PowerLevel.MEDIUM, PowerLevel.HIGH]
        return levels.index(cur.power_level) >= levels.index(self._min_level)

    def schedule(self, workload: dict[str, Any]) -> dict[str, Any]:
        """Attempt to schedule a workload.

        If energy conditions are insufficient, the workload is deferred.

        Parameters
        ----------
        workload : dict
            Arbitrary workload descriptor.

        Returns
        -------
        dict
            A result dict with keys ``scheduled`` (bool) and
            ``deferred_count`` (int).
        """
        if self.can_schedule():
            return {"scheduled": True, "deferred_count": len(self._deferred)}
        else:
            self._deferred.append(workload)
            return {"scheduled": False, "deferred_count": len(self._deferred)}

    def flush_deferred(self) -> list[dict[str, Any]]:
        """Return and clear all deferred workloads (call when power improves)."""
        items = list(self._deferred)
        self._deferred.clear()
        return items
