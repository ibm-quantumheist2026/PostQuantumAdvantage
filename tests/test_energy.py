"""Tests for quantum_telemetry.energy."""

import pytest

from quantum_telemetry.energy import (
    EnergyAwareScheduler,
    EnergyMonitor,
    EnergyState,
    PowerLevel,
)


class TestEnergyState:
    def test_high_availability_maps_to_high(self):
        state = EnergyState.from_metrics(compute_load=0.1, energy_utilization=0.1)
        assert state.power_level == PowerLevel.HIGH

    def test_medium_availability(self):
        state = EnergyState.from_metrics(compute_load=0.5, energy_utilization=0.6)
        assert state.power_level == PowerLevel.MEDIUM

    def test_low_availability(self):
        state = EnergyState.from_metrics(compute_load=0.9, energy_utilization=0.9)
        assert state.power_level == PowerLevel.LOW

    def test_clamping(self):
        state = EnergyState.from_metrics(compute_load=5.0, energy_utilization=-1.0)
        assert 0.0 <= state.compute_load <= 1.0
        assert 0.0 <= state.energy_utilization <= 1.0

    def test_contributes_to_grid_when_surplus(self):
        state = EnergyState.from_metrics(compute_load=0.05, energy_utilization=0.05)
        assert state.contributes_to_grid is True

    def test_does_not_contribute_when_busy(self):
        state = EnergyState.from_metrics(compute_load=0.8, energy_utilization=0.8)
        assert state.contributes_to_grid is False


class TestEnergyMonitor:
    def test_initial_current_is_none(self):
        monitor = EnergyMonitor()
        assert monitor.current is None

    def test_record_returns_state(self):
        monitor = EnergyMonitor()
        state = monitor.record(0.3, 0.4)
        assert isinstance(state, EnergyState)

    def test_current_updates(self):
        monitor = EnergyMonitor()
        monitor.record(0.1, 0.1)
        monitor.record(0.9, 0.9)
        assert monitor.current.power_level == PowerLevel.LOW

    def test_history_grows(self):
        monitor = EnergyMonitor()
        for i in range(5):
            monitor.record(0.1 * i, 0.1 * i)
        assert len(monitor.history) == 5

    def test_history_bounded(self):
        monitor = EnergyMonitor(history_limit=3)
        for i in range(10):
            monitor.record(0.1, 0.1)
        assert len(monitor.history) == 3

    def test_average_utilization(self):
        monitor = EnergyMonitor()
        monitor.record(0.0, 0.2)
        monitor.record(0.0, 0.4)
        avg = monitor.average_utilization()
        assert abs(avg - 0.3) < 1e-6

    def test_summary_keys(self):
        monitor = EnergyMonitor()
        monitor.record(0.3, 0.5)
        summary = monitor.summary()
        assert "current_power_level" in summary
        assert "current_load" in summary
        assert "current_utilization" in summary
        assert "average_utilization" in summary
        assert "contributes_to_grid" in summary


class TestEnergyAwareScheduler:
    def test_schedules_when_power_sufficient(self):
        monitor = EnergyMonitor()
        monitor.record(0.1, 0.1)  # HIGH power
        scheduler = EnergyAwareScheduler(monitor, PowerLevel.MEDIUM)
        result = scheduler.schedule({"job": "train"})
        assert result["scheduled"] is True

    def test_defers_when_power_insufficient(self):
        monitor = EnergyMonitor()
        monitor.record(0.9, 0.9)  # LOW power
        scheduler = EnergyAwareScheduler(monitor, PowerLevel.MEDIUM)
        result = scheduler.schedule({"job": "train"})
        assert result["scheduled"] is False
        assert result["deferred_count"] == 1

    def test_flush_clears_deferred(self):
        monitor = EnergyMonitor()
        monitor.record(0.9, 0.9)  # LOW power
        scheduler = EnergyAwareScheduler(monitor, PowerLevel.MEDIUM)
        scheduler.schedule({"job": "a"})
        scheduler.schedule({"job": "b"})
        items = scheduler.flush_deferred()
        assert len(items) == 2
        assert scheduler.flush_deferred() == []

    def test_schedules_without_any_readings(self):
        monitor = EnergyMonitor()  # no readings recorded
        scheduler = EnergyAwareScheduler(monitor)
        result = scheduler.schedule({"job": "optimistic"})
        assert result["scheduled"] is True
