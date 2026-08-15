"""Tests for the wellfile agent pipeline."""

from unittest.mock import MagicMock, patch


from mt_oil.schemas.wellfile import (
    CompletionSpecs,
    ProductionSummary,
    WellfileAgentResponse,
    WellfileExtraction,
)


class TestSchemas:
    def test_completion_specs_defaults(self):
        specs = CompletionSpecs(api_number="2508323399")
        assert specs.api_number == "2508323399"
        assert specs.tvd_ft is None
        assert specs.lateral_length_ft is None

    def test_completion_specs_full(self):
        specs = CompletionSpecs(
            api_number="2508323399",
            well_name="WELL 1",
            tvd_ft=10450.0,
            md_ft=20300.0,
            lateral_length_ft=9850.0,
            total_clean_fluid_bbls=85000.0,
            total_proppant_lbs=12300000.0,
            max_treating_pressure_psi=8500.0,
            casing_intermediate_depth_ft=2100.0,
        )
        assert specs.tvd_ft == 10450.0
        assert specs.total_proppant_lbs == 12300000.0

    def test_wellfile_extraction_success(self):
        specs = CompletionSpecs(api_number="2508323399")
        ext = WellfileExtraction(
            api_number="2508323399",
            specs=specs,
            extraction_status="SUCCESS",
        )
        assert ext.extraction_status == "SUCCESS"
        assert ext.cache_hit is False

    def test_wellfile_extraction_failed(self):
        ext = WellfileExtraction(
            api_number="2508323399",
            extraction_status="FAILED_PARSING",
        )
        assert ext.extraction_status == "FAILED_PARSING"
        assert ext.specs is None

    def test_wellfile_agent_response_cache_hit(self):
        resp = WellfileAgentResponse(
            api_number="2508323399",
            extraction_status="SUCCESS",
            cache_hit=True,
        )
        assert resp.cache_hit is True

    def test_production_summary(self):
        summary = ProductionSummary(
            total_months=24,
            peak_oil_bbls=1000.0,
            peak_gas_mcf=500.0,
            eur_boe=450000.0,
            dca_method="duong",
        )
        assert summary.total_months == 24
        assert summary.dca_method == "duong"

    def test_intensity_metrics_computation(self):
        specs = CompletionSpecs(
            api_number="2508323399",
            lateral_length_ft=9850.0,
            total_proppant_lbs=12300000.0,
            total_clean_fluid_bbls=85000.0,
        )
        proppant_int = specs.total_proppant_lbs / specs.lateral_length_ft
        fluid_int = specs.total_clean_fluid_bbls / specs.lateral_length_ft
        assert round(proppant_int, 2) == 1248.73
        assert round(fluid_int, 2) == 8.63

    def test_intensity_zero_lateral(self):
        specs = CompletionSpecs(
            api_number="2508323399",
            lateral_length_ft=0,
            total_proppant_lbs=12300000.0,
        )
        assert specs.lateral_length_ft == 0


class TestBqCacheCheck:
    @patch("mt_oil.agents.tools.document._check_bq_cache")
    def test_cache_hit_returns_data(self, mock_check):
        mock_check.return_value = {
            "api_number": "2508323399",
            "well_name": "WELL 1",
            "tvd_ft": 10450.0,
            "lateral_length_ft": 9850.0,
            "total_proppant_lbs": 12300000.0,
            "extraction_status": "SUCCESS",
        }
        result = mock_check("2508323399")
        assert result is not None
        assert result["extraction_status"] == "SUCCESS"
        assert result["tvd_ft"] == 10450.0

    @patch("mt_oil.agents.tools.document._check_bq_cache")
    def test_cache_miss_returns_none(self, mock_check):
        mock_check.return_value = None
        result = mock_check("2508323399")
        assert result is None


class TestIntensityComputation:
    def test_both_intensities(self):
        from mt_oil.api.routes.agent import _compute_intensity

        completion = {
            "lateral_length_ft": 9850.0,
            "total_proppant_lbs": 12300000.0,
            "total_clean_fluid_bbls": 85000.0,
        }
        proppant, fluid = _compute_intensity(completion)
        assert proppant == 1248.73
        assert fluid == 8.63

    def test_no_lateral_returns_none(self):
        from mt_oil.api.routes.agent import _compute_intensity

        completion = {
            "lateral_length_ft": None,
            "total_proppant_lbs": 12300000.0,
        }
        proppant, fluid = _compute_intensity(completion)
        assert proppant is None
        assert fluid is None

    def test_no_completion_specs(self):
        from mt_oil.api.routes.agent import _compute_intensity

        proppant, fluid = _compute_intensity(None)
        assert proppant is None
        assert fluid is None

    def test_partial_data(self):
        from mt_oil.api.routes.agent import _compute_intensity

        completion = {
            "lateral_length_ft": 9850.0,
            "total_proppant_lbs": 12300000.0,
            "total_clean_fluid_bbls": None,
        }
        proppant, fluid = _compute_intensity(completion)
        assert proppant == 1248.73
        assert fluid is None


class TestProductionSummaryBuilder:
    def test_full_data(self):
        from mt_oil.api.routes.agent import _build_production_summary

        prod = {
            "total_months": 24,
            "peak_oil_bbls": 1500.0,
            "peak_gas_mcf": 800.0,
            "eur_boe": 450000.0,
            "dca_method": "duong",
        }
        summary = _build_production_summary(prod)
        assert summary.total_months == 24
        assert summary.peak_oil_bbls == 1500.0
        assert summary.peak_gas_mcf == 800.0
        assert summary.eur_boe == 450000.0
        assert summary.dca_method == "duong"

    def test_empty_data(self):
        from mt_oil.api.routes.agent import _build_production_summary

        summary = _build_production_summary({})
        assert summary.total_months == 0
        assert summary.peak_oil_bbls == 0.0
        assert summary.peak_gas_mcf == 0.0
        assert summary.eur_boe is None
        assert summary.dca_method is None

    def test_partial_data(self):
        from mt_oil.api.routes.agent import _build_production_summary

        prod = {"total_months": 6, "peak_oil_bbls": 500}
        summary = _build_production_summary(prod)
        assert summary.total_months == 6
        assert summary.peak_oil_bbls == 500.0
        assert summary.peak_gas_mcf == 0.0
        assert summary.eur_boe is None
        assert summary.dca_method is None

    def test_null_values(self):
        from mt_oil.api.routes.agent import _build_production_summary

        prod = {"total_months": None, "peak_oil_bbls": None, "eur_boe": None}
        summary = _build_production_summary(prod)
        assert summary.total_months == 0
        assert summary.peak_oil_bbls == 0.0
        assert summary.eur_boe is None


class TestGcsBlobName:
    @patch("mt_oil.agents.tools.document._gcs_blob_name")
    def test_blob_name_format(self, mock_name):
        mock_name.return_value = "wells/pdfs/25083233990000/2508323399.pdf"
        result = mock_name("25083233990000")
        assert result == "wells/pdfs/25083233990000/2508323399.pdf"


class TestProductionTool:
    @patch("mt_oil.agents.tools.production._get_loader")
    def test_no_loader_returns_error(self, mock_get_loader):
        mock_get_loader.return_value = None
        from mt_oil.agents.tools.production import bq_production_tool

        result = bq_production_tool("2508323399")
        assert result["total_months"] == 0
        assert "error" in result

    @patch("mt_oil.agents.tools.production._get_loader")
    def test_empty_production(self, mock_get_loader):
        import pandas as pd

        mock_loader = MagicMock()
        mock_loader.load_production_for_well.return_value = pd.DataFrame()
        mock_get_loader.return_value = mock_loader

        from mt_oil.agents.tools.production import bq_production_tool

        result = bq_production_tool("2508323399")
        assert result["total_months"] == 0


class TestWellfileExtraction:
    @patch("mt_oil.agents.tools.document._check_bq_cache")
    def test_extract_cache_hit(self, mock_check):
        mock_check.return_value = {
            "api_number": "2508323399",
            "well_name": "WELL 1",
            "tvd_ft": 10450.0,
            "extraction_status": "SUCCESS",
        }
        from mt_oil.agents.tools.document import wellfile_document_tool

        result = wellfile_document_tool("2508323399")
        assert result["extraction_status"] == "SUCCESS"
        assert result.get("tvd_ft") == 10450.0

    @patch("mt_oil.agents.tools.document._check_bq_cache")
    @patch("mt_oil.agents.tools.document._read_pdf_from_gcs")
    def test_extract_pdf_not_found(self, mock_read, mock_check):
        mock_check.return_value = None
        mock_read.return_value = None

        from mt_oil.agents.tools.document import wellfile_document_tool

        result = wellfile_document_tool("2508323399")
        assert result["extraction_status"] == "FAILED_PARSING"


class TestAgentResponseParsing:
    def test_parse_valid_json(self):
        from mt_oil.api.routes.agent import _parse_agent_response

        text = '{"extraction_status": "SUCCESS", "cache_hit": false, "completion_specs": {"api_number": "2508323399", "lateral_length_ft": 9850.0}}'
        resp = _parse_agent_response("2508323399", text)
        assert resp.extraction_status == "SUCCESS"
        assert resp.completion_specs is not None
        assert resp.completion_specs.lateral_length_ft == 9850.0

    def test_parse_invalid_json(self):
        from mt_oil.api.routes.agent import _parse_agent_response

        resp = _parse_agent_response("2508323399", "not json at all")
        assert resp.extraction_status == "FAILED_PARSING"

    def test_parse_with_code_fence(self):
        from mt_oil.api.routes.agent import _parse_agent_response

        text = '```json\n{"extraction_status": "SUCCESS", "cache_hit": true}\n```'
        resp = _parse_agent_response("2508323399", text)
        assert resp.extraction_status == "SUCCESS"
        assert resp.cache_hit is True

    def test_parse_flat_json(self):
        from mt_oil.api.routes.agent import _parse_agent_response

        text = '{"api_number": "2508323399", "extraction_status": "SUCCESS", "tvd_ft": 10450.0}'
        resp = _parse_agent_response("2508323399", text)
        assert resp.extraction_status == "SUCCESS"
        assert resp.completion_specs is not None
        assert resp.completion_specs.tvd_ft == 10450.0
