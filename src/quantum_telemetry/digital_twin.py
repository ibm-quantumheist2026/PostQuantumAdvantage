"""Digital-twin simulation pipeline for the QA11dSH platform.

Implements the five-stage digital-twin pipeline::

    data ingestion
     → model generation
     → twin simulation
     → optimization
     → feedback update

Supported domains include healthcare (patient-specific simulation,
treatment optimization, drug interaction modelling) and infrastructure
(energy grid, supply chain, climate).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Domain(str, Enum):
    """Application domains for digital-twin models."""

    HEALTHCARE = "healthcare"
    ENERGY_GRID = "energy_grid"
    SUPPLY_CHAIN = "supply_chain"
    CLIMATE = "climate"
    GENERIC = "generic"


@dataclass
class TwinModel:
    """A generated digital-twin model.

    Attributes
    ----------
    model_id : str
        Unique identifier.
    domain : Domain
        The application domain.
    parameters : dict[str, Any]
        Model parameters derived during generation.
    metadata : dict[str, Any]
        Additional metadata captured during ingestion.
    """

    model_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    domain: Domain = Domain.GENERIC
    parameters: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SimulationResult:
    """Output produced by running a twin simulation.

    Attributes
    ----------
    run_id : str
        Unique run identifier.
    model_id : str
        The model that was simulated.
    outputs : dict[str, Any]
        Simulation outputs.
    optimized_parameters : dict[str, Any]
        Parameter adjustments suggested by the optimizer.
    feedback : dict[str, Any]
        Feedback values fed back into the model.
    elapsed_seconds : float
        Wall-clock time for the simulation step.
    """

    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model_id: str = ""
    outputs: dict[str, Any] = field(default_factory=dict)
    optimized_parameters: dict[str, Any] = field(default_factory=dict)
    feedback: dict[str, Any] = field(default_factory=dict)
    elapsed_seconds: float = 0.0


class DigitalTwinPipeline:
    """Five-stage digital-twin pipeline.

    Usage::

        pipeline = DigitalTwinPipeline(domain=Domain.HEALTHCARE)
        result = pipeline.run(raw_data)

    Stages
    ------
    1. :meth:`ingest`    – normalise raw data.
    2. :meth:`generate`  – build a domain-specific twin model.
    3. :meth:`simulate`  – run the model forward.
    4. :meth:`optimize`  – adjust parameters to improve outcomes.
    5. :meth:`feedback`  – propagate adjustments back to the model.
    """

    def __init__(self, domain: Domain = Domain.GENERIC) -> None:
        self.domain = domain
        self._models: dict[str, TwinModel] = {}

    # ------------------------------------------------------------------
    # Pipeline stages
    # ------------------------------------------------------------------

    def ingest(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Stage 1 – Normalise and validate raw input data.

        Parameters
        ----------
        raw_data : dict
            Arbitrary key–value data (sensor readings, patient records, etc.).

        Returns
        -------
        dict
            Normalised data record with a ``timestamp`` field added.
        """
        normalised = {str(k): v for k, v in raw_data.items()}
        normalised.setdefault("timestamp", time.time())
        normalised.setdefault("domain", self.domain.value)
        return normalised

    # Keys added automatically by :meth:`ingest` that should not become model
    # parameters -- they are metadata, not domain measurements.
    INGEST_META_KEYS: frozenset[str] = frozenset({"timestamp", "domain"})

    def generate(self, ingested: dict[str, Any]) -> TwinModel:
        """Stage 2 – Build (or update) a twin model from ingested data.

        Parameters
        ----------
        ingested : dict
            Output of :meth:`ingest`.

        Returns
        -------
        TwinModel
            A new model whose parameters are derived from *ingested*.
        """
        params: dict[str, Any] = {}
        for key, value in ingested.items():
            if key in self.INGEST_META_KEYS:
                continue
            if isinstance(value, (int, float)):
                params[key] = float(value)

        model = TwinModel(
            domain=self.domain,
            parameters=params,
            metadata={"source_keys": list(ingested.keys())},
        )
        self._models[model.model_id] = model
        return model

    def simulate(self, model: TwinModel) -> dict[str, Any]:
        """Stage 3 – Run the model forward to produce simulation outputs.

        Parameters
        ----------
        model : TwinModel
            The twin model to simulate.

        Returns
        -------
        dict
            Simulation outputs, including a ``predicted_outcome`` value.
        """
        params = model.parameters
        if not params:
            return {"predicted_outcome": 0.0, "confidence": 0.0}

        values = list(params.values())
        mean = sum(values) / len(values)
        predicted = mean * 0.95  # simplified model
        confidence = min(1.0, len(values) / 10.0)

        return {
            "predicted_outcome": predicted,
            "confidence": confidence,
            "n_parameters": len(params),
        }

    def optimize(
        self,
        model: TwinModel,
        simulation_outputs: dict[str, Any],
    ) -> dict[str, Any]:
        """Stage 4 – Suggest parameter adjustments to improve outcomes.

        Parameters
        ----------
        model : TwinModel
            The twin model.
        simulation_outputs : dict
            Output of :meth:`simulate`.

        Returns
        -------
        dict
            Suggested parameter deltas keyed by parameter name.
        """
        confidence = float(simulation_outputs.get("confidence", 0.5))
        adjustment_factor = 1.0 - confidence  # less confident → more adjustment

        deltas: dict[str, Any] = {
            k: v * adjustment_factor * 0.1
            for k, v in model.parameters.items()
        }
        return deltas

    def feedback(
        self,
        model: TwinModel,
        optimized_parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Stage 5 – Apply feedback to propagate adjustments back to model.

        Parameters
        ----------
        model : TwinModel
            The twin model to update.
        optimized_parameters : dict
            Output of :meth:`optimize`.

        Returns
        -------
        dict
            Summary of the feedback step.
        """
        updated: dict[str, float] = {}
        for key, delta in optimized_parameters.items():
            old = float(model.parameters.get(key, 0.0))
            new = old + float(delta)
            model.parameters[key] = new
            updated[key] = new

        return {"updated_parameters": updated, "model_id": model.model_id}

    # ------------------------------------------------------------------
    # Convenience: run the full pipeline
    # ------------------------------------------------------------------

    def run(self, raw_data: dict[str, Any]) -> SimulationResult:
        """Execute all five stages and return a :class:`SimulationResult`.

        Parameters
        ----------
        raw_data : dict
            Arbitrary input data.

        Returns
        -------
        SimulationResult
            Consolidated output from all pipeline stages.
        """
        start = time.time()

        ingested = self.ingest(raw_data)
        model = self.generate(ingested)
        outputs = self.simulate(model)
        optimized = self.optimize(model, outputs)
        fb = self.feedback(model, optimized)

        return SimulationResult(
            model_id=model.model_id,
            outputs=outputs,
            optimized_parameters=optimized,
            feedback=fb,
            elapsed_seconds=time.time() - start,
        )
