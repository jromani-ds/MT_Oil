"""Tests for the wellfile agent pipeline."""

from unittest.mock import MagicMock, patch

from mt_oil.schemas.wellfile import (
    BitRun,
    CasingCementData,
    CasingString,
    CementEvaluation,
    CementOperation,
    CompletionSpecs,
    CompletionStimulationData,
    DownholeTubulars,
    DrillingData,
    DrillingFluidParams,
    FormationTop,
    GeologyData,
    HydrocarbonShow,
    IpFlowTest,
    MultiStageTool,
    Perforation,
    ProductionSummary,
    StimulationStage,
    WellboreEvent,
    WellfileAgentResponse,
    WellfileExtraction,
    WellfileExtractionPayload,
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

    def test_wellfile_agent_response_with_payload(self):
        payload = WellfileExtractionPayload()
        resp = WellfileAgentResponse(
            api_number="2508323399",
            extraction_status="SUCCESS",
            wellfile_data=payload,
        )
        assert resp.wellfile_data is not None
        assert resp.wellfile_data.completion_stimulation is None

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

    # ── new leaf model tests ──

    def test_ip_flow_test_defaults(self):
        ip = IpFlowTest()
        assert ip.test_duration_hrs is None
        assert ip.test_method is None

    def test_ip_flow_test_full(self):
        ip = IpFlowTest(
            test_duration_hrs=24.0,
            oil_rate_24hr_bbls=500.0,
            gas_rate_24hr_mcf=1000.0,
            water_rate_24hr_bbls=10.0,
            choke_size_inches=0.5,
            flowing_tubing_pressure_psi=2000.0,
            shut_in_tubing_pressure_psi=3000.0,
            test_method="flowing",
        )
        assert ip.oil_rate_24hr_bbls == 500.0
        assert ip.test_method == "flowing"

    def test_perforation_defaults(self):
        p = Perforation()
        assert p.top_md_ft is None
        assert p.status is None

    def test_perforation_full(self):
        p = Perforation(
            top_md_ft=10000.0,
            bottom_md_ft=10100.0,
            shots_per_ft=6.0,
            gun_charge_diameter_in=0.5,
            gun_type="Hollow carrier",
            phase_angle_deg=60.0,
            formation_name="Three Forks",
            status="open",
        )
        assert p.shots_per_ft == 6.0
        assert p.status == "open"

    def test_stimulation_stage_defaults(self):
        s = StimulationStage()
        assert s.treatment_type is None
        assert s.stage_number is None

    def test_stimulation_stage_full(self):
        s = StimulationStage(
            treatment_type="Hydraulic Fracture",
            stage_number=1,
            fluid_volume_bbls=15000.0,
            chemical_additives="FR-1 0.5 gpt",
            diverter_specs="Ball sealers 20",
            max_treating_pressure_psi=8500.0,
            avg_treating_pressure_psi=7200.0,
            injection_rate_bpm=60.0,
            isip_psi=4500.0,
        )
        assert s.treatment_type == "Hydraulic Fracture"
        assert s.isip_psi == 4500.0

    def test_downhole_tubulars_defaults(self):
        dt = DownholeTubulars()
        assert dt.tubing_od_in is None
        assert dt.applied_pretension_lbs is None

    def test_formation_top_defaults(self):
        ft = FormationTop()
        assert ft.formation_name is None
        assert ft.pick_source is None

    def test_hydrocarbon_show_defaults(self):
        hs = HydrocarbonShow()
        assert hs.peak_gas_units is None
        assert hs.c1_ppm is None

    def test_casing_string_defaults(self):
        cs = CasingString()
        assert cs.string_type is None
        assert cs.burst_rating_psi is None

    def test_cement_operation_defaults(self):
        co = CementOperation()
        assert co.slurry_volume_sacks is None
        assert co.bump_pressure_psi is None

    def test_multi_stage_tool_defaults(self):
        mt = MultiStageTool()
        assert mt.stage_tool_depth_ft is None

    def test_cement_evaluation_defaults(self):
        ce = CementEvaluation()
        assert ce.logged_toc_ft is None
        assert ce.verification_method is None

    def test_drilling_fluid_params_defaults(self):
        df = DrillingFluidParams()
        assert df.mud_weight_ppg is None
        assert df.oil_water_ratio is None

    def test_bit_run_defaults(self):
        br = BitRun()
        assert br.bit_number is None
        assert br.avg_rop_ft_per_hr is None

    def test_wellbore_event_defaults(self):
        we = WellboreEvent()
        assert we.event_type is None
        assert we.description is None

    # ── category model tests ──

    def test_completion_stimulation_data_defaults(self):
        cs = CompletionStimulationData()
        assert cs.tvd_ft is None
        assert cs.perforations == []
        assert cs.ip_flow_test is None

    def test_geology_data_defaults(self):
        g = GeologyData()
        assert g.formation_tops == []
        assert g.hydrocarbon_shows == []

    def test_casing_cement_data_defaults(self):
        cc = CasingCementData()
        assert cc.casing_program == []
        assert cc.cement_evaluation is None

    def test_drilling_data_defaults(self):
        d = DrillingData()
        assert d.drilling_fluid_params == []
        assert d.bit_runs == []

    def test_wellfile_extraction_payload_defaults(self):
        p = WellfileExtractionPayload()
        assert p.completion_stimulation is None
        assert p.geology is None
        assert p.casing_cement is None
        assert p.drilling is None

    def test_wellfile_extraction_payload_full(self):
        cs = CompletionStimulationData(tvd_ft=10450.0)
        geo = GeologyData()
        cc = CasingCementData()
        drill = DrillingData()
        p = WellfileExtractionPayload(
            completion_stimulation=cs,
            geology=geo,
            casing_cement=cc,
            drilling=drill,
        )
        assert p.completion_stimulation.tvd_ft == 10450.0
        assert p.geology is not None


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

    # ── new: payload cache section test ──

    @patch("mt_oil.agents.tools.document._read_payload_from_bq")
    def test_check_bq_cache_section_hit(self, mock_read):
        mock_read.return_value = {
            "completion_stimulation": {"tvd_ft": 10450.0, "well_name": "TEST"},
        }
        from mt_oil.agents.tools.document import _check_bq_cache_section

        result = _check_bq_cache_section("2508323399", "completion_stimulation")
        assert result is not None
        assert result["tvd_ft"] == 10450.0

    @patch("mt_oil.agents.tools.document._read_payload_from_bq")
    def test_check_bq_cache_section_miss(self, mock_read):
        mock_read.return_value = {"completion_stimulation": None}
        from mt_oil.agents.tools.document import _check_bq_cache_section

        result = _check_bq_cache_section("2508323399", "completion_stimulation")
        assert result is None

    @patch("mt_oil.agents.tools.document._read_payload_from_bq")
    def test_check_bq_cache_section_no_payload(self, mock_read):
        mock_read.return_value = None
        from mt_oil.agents.tools.document import _check_bq_cache_section

        result = _check_bq_cache_section("2508323399", "completion_stimulation")
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
    @patch("mt_oil.agents.tools.document._check_bq_cache_section")
    def test_extract_cache_hit(self, mock_cache_section):
        mock_cache_section.return_value = {
            "tvd_ft": 10450.0,
            "well_name": "WELL 1",
        }
        from mt_oil.agents.tools.document import wellfile_document_tool

        result = wellfile_document_tool("2508323399")
        assert result["extraction_status"] == "SUCCESS"
        assert result.get("cache_hit") is True
        cs = result.get("completion_stimulation", {})
        assert cs.get("tvd_ft") == 10450.0

    @patch("mt_oil.agents.tools.document._check_bq_cache_section")
    @patch("mt_oil.agents.tools.document._read_pdf")
    def test_extract_pdf_not_found(self, mock_read, mock_cache_section):
        mock_cache_section.return_value = None
        mock_read.return_value = None

        from mt_oil.agents.tools.document import wellfile_document_tool

        result = wellfile_document_tool("2508323399")
        assert result["extraction_status"] == "FAILED_PARSING"

    # ── new: section tool cache hit tests ──

    @patch("mt_oil.agents.tools.document._check_bq_cache_section")
    def test_completion_tool_cache_hit(self, mock_cache):
        mock_cache.return_value = {"tvd_ft": 10450.0, "well_name": "TEST"}
        from mt_oil.agents.tools.document import wellfile_completion_tool

        result = wellfile_completion_tool("2508323399")
        assert result["extraction_status"] == "SUCCESS"
        assert result["cache_hit"] is True
        assert result["completion_stimulation"]["tvd_ft"] == 10450.0

    @patch("mt_oil.agents.tools.document._check_bq_cache_section")
    @patch("mt_oil.agents.tools.document._read_pdf")
    def test_completion_tool_pdf_not_found(self, mock_read, mock_cache):
        mock_cache.return_value = None
        mock_read.return_value = None
        from mt_oil.agents.tools.document import wellfile_completion_tool

        result = wellfile_completion_tool("2508323399")
        assert result["extraction_status"] == "FAILED_PARSING"

    @patch("mt_oil.agents.tools.document._check_bq_cache_section")
    def test_geology_tool_cache_hit(self, mock_cache):
        mock_cache.return_value = {"formation_tops": []}
        from mt_oil.agents.tools.document import wellfile_geology_tool

        result = wellfile_geology_tool("2508323399")
        assert result["extraction_status"] == "SUCCESS"
        assert result["cache_hit"] is True
        assert result["geology"]["formation_tops"] == []

    @patch("mt_oil.agents.tools.document._check_bq_cache_section")
    def test_casing_tool_cache_hit(self, mock_cache):
        mock_cache.return_value = {"casing_program": []}
        from mt_oil.agents.tools.document import wellfile_casing_tool

        result = wellfile_casing_tool("2508323399")
        assert result["extraction_status"] == "SUCCESS"
        assert result["cache_hit"] is True

    @patch("mt_oil.agents.tools.document._check_bq_cache_section")
    def test_drilling_tool_cache_hit(self, mock_cache):
        mock_cache.return_value = {"bit_runs": []}
        from mt_oil.agents.tools.document import wellfile_drilling_tool

        result = wellfile_drilling_tool("2508323399")
        assert result["extraction_status"] == "SUCCESS"
        assert result["cache_hit"] is True


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

    # ── new: parse with wellfile_data ──

    def test_parse_with_wellfile_data(self):
        from mt_oil.api.routes.agent import _parse_agent_response

        text = """{
            "extraction_status": "SUCCESS",
            "cache_hit": false,
            "wellfile_data": {
                "completion_stimulation": {"tvd_ft": 10450.0},
                "geology": {"formation_tops": [{"formation_name": "Three Forks", "md_ft": 10000.0}]}
            }
        }"""
        resp = _parse_agent_response("2508323399", text)
        assert resp.extraction_status == "SUCCESS"
        assert resp.wellfile_data is not None
        assert resp.wellfile_data.completion_stimulation is not None
        assert resp.wellfile_data.completion_stimulation.tvd_ft == 10450.0
        assert resp.wellfile_data.geology is not None
        assert len(resp.wellfile_data.geology.formation_tops) == 1

    def test_parse_with_top_level_sections(self):
        """Test fallback when sections are at top level instead of inside wellfile_data."""
        from mt_oil.api.routes.agent import _parse_agent_response

        text = """{
            "extraction_status": "SUCCESS",
            "completion_stimulation": {"tvd_ft": 10450.0},
            "drilling": {"bit_runs": [{"bit_number": 1}]}
        }"""
        resp = _parse_agent_response("2508323399", text)
        assert resp.extraction_status == "SUCCESS"
        assert resp.wellfile_data is not None
        assert resp.wellfile_data.drilling is not None
        assert len(resp.wellfile_data.drilling.bit_runs) == 1


class TestFlatFromPayload:
    def test_flat_from_payload(self):
        from mt_oil.api.routes.agent import _flat_from_payload

        payload = {
            "completion_stimulation": {
                "well_name": "TEST",
                "tvd_ft": 10450.0,
                "md_ft": 20000.0,
            }
        }
        flat = _flat_from_payload(payload)
        assert flat["well_name"] == "TEST"
        assert flat["tvd_ft"] == 10450.0

    def test_flat_from_empty_payload(self):
        from mt_oil.api.routes.agent import _flat_from_payload

        flat = _flat_from_payload({})
        assert flat["well_name"] is None
        assert flat["tvd_ft"] is None


class TestWriteSectionToBq:
    @patch("mt_oil.agents.tools.document.settings")
    @patch("mt_oil.agents.tools.document.bigquery.Client")
    @patch("mt_oil.agents.tools.document._read_payload_from_bq")
    def test_write_section_merges_payload(self, mock_read, mock_bq, mock_settings):
        from mt_oil.agents.telemetry import Timer
        from mt_oil.agents.tools.document import _write_section_to_bq

        mock_settings.gcp_project_id = "test-project"
        mock_settings.bigquery_dataset = "test_dataset"
        mock_settings.wellfile_parsed_table = "wellfile_parsed_metadata"
        mock_read.return_value = {"completion_stimulation": {"old": "data"}}
        mock_client = MagicMock()
        mock_bq.return_value = mock_client

        timer = Timer()
        timer.__enter__()
        timer.__exit__()

        _write_section_to_bq(
            "2508323399",
            "geology",
            {"formation_tops": []},
            "gs://bucket/pdf.pdf",
            timer,
        )

        assert mock_client.query.called
