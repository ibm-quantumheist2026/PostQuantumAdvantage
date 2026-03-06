"""Tests for quantum_telemetry.digital_twin."""

import pytest

from quantum_telemetry.digital_twin import DigitalTwinPipeline, Domain, SimulationResult


class TestDigitalTwinPipelineIngest:
    def test_adds_timestamp(self):
        pipeline = DigitalTwinPipeline()
        result = pipeline.ingest({"glucose": 5.4})
        assert "timestamp" in result

    def test_adds_domain_field(self):
        pipeline = DigitalTwinPipeline(domain=Domain.HEALTHCARE)
        result = pipeline.ingest({"x": 1})
        assert result["domain"] == Domain.HEALTHCARE.value

    def test_preserves_input_data(self):
        pipeline = DigitalTwinPipeline()
        result = pipeline.ingest({"a": 1, "b": 2})
        assert result["a"] == 1
        assert result["b"] == 2


class TestDigitalTwinPipelineGenerate:
    def test_produces_twin_model(self):
        pipeline = DigitalTwinPipeline()
        ingested = pipeline.ingest({"val": 10.0})
        model = pipeline.generate(ingested)
        assert model.model_id
        assert model.domain == Domain.GENERIC

    def test_numeric_fields_become_parameters(self):
        pipeline = DigitalTwinPipeline()
        ingested = pipeline.ingest({"x": 3.5, "label": "abc"})
        model = pipeline.generate(ingested)
        assert "x" in model.parameters
        assert "label" not in model.parameters


class TestDigitalTwinPipelineSimulate:
    def test_returns_predicted_outcome(self):
        pipeline = DigitalTwinPipeline()
        ingested = pipeline.ingest({"a": 2.0})
        model = pipeline.generate(ingested)
        output = pipeline.simulate(model)
        assert "predicted_outcome" in output
        assert "confidence" in output

    def test_empty_parameters(self):
        pipeline = DigitalTwinPipeline()
        ingested = pipeline.ingest({"label": "only_string"})
        model = pipeline.generate(ingested)
        output = pipeline.simulate(model)
        assert output["predicted_outcome"] == 0.0


class TestDigitalTwinPipelineOptimize:
    def test_returns_deltas(self):
        pipeline = DigitalTwinPipeline()
        ingested = pipeline.ingest({"v": 100.0})
        model = pipeline.generate(ingested)
        outputs = pipeline.simulate(model)
        deltas = pipeline.optimize(model, outputs)
        assert "v" in deltas

    def test_high_confidence_small_adjustment(self):
        pipeline = DigitalTwinPipeline()
        ingested = pipeline.ingest({str(i): 1.0 for i in range(10)})
        model = pipeline.generate(ingested)
        outputs = pipeline.simulate(model)
        # confidence should be at maximum (1.0) → delta ≈ 0
        deltas = pipeline.optimize(model, {"confidence": 1.0})
        for delta in deltas.values():
            assert abs(delta) < 1e-9


class TestDigitalTwinPipelineFeedback:
    def test_updates_model_parameters(self):
        pipeline = DigitalTwinPipeline()
        ingested = pipeline.ingest({"p": 50.0})
        model = pipeline.generate(ingested)
        original_p = model.parameters["p"]
        deltas = {"p": 5.0}
        fb = pipeline.feedback(model, deltas)
        assert model.parameters["p"] == original_p + 5.0
        assert "updated_parameters" in fb

    def test_returns_model_id(self):
        pipeline = DigitalTwinPipeline()
        ingested = pipeline.ingest({"q": 1.0})
        model = pipeline.generate(ingested)
        fb = pipeline.feedback(model, {})
        assert fb["model_id"] == model.model_id


class TestDigitalTwinPipelineRun:
    def test_full_pipeline_returns_simulation_result(self):
        pipeline = DigitalTwinPipeline(domain=Domain.HEALTHCARE)
        result = pipeline.run({"patient_id_hash": 42, "glucose": 5.4, "bp": 120.0})
        assert isinstance(result, SimulationResult)
        assert result.model_id
        assert result.elapsed_seconds >= 0

    def test_outputs_keys_present(self):
        pipeline = DigitalTwinPipeline()
        result = pipeline.run({"x": 1.0})
        assert "predicted_outcome" in result.outputs

    def test_healthcare_domain(self):
        pipeline = DigitalTwinPipeline(domain=Domain.HEALTHCARE)
        result = pipeline.run({"score": 0.9})
        assert result.model_id  # just confirm it completes without error
