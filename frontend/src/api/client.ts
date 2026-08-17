import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export interface Well {
    API_WellNo: string;
    Lat: number;
    Long: number;
    Slant?: string;
    Type?: string;
}

export interface ProductionRecord {
    Rpt_Date: string;
    BBLS_OIL_COND: number;
    MCF_GAS: number;
    BBLS_WTR: number;
    DAYS_PROD: number;
}

export interface DeclineFit {
    method: string;
    score: number;
    params: Record<string, number>;
}

export interface Forecast {
    months: number[];
    production: number[];
}

export interface DeclineResponse {
    historical_data_points: number;
    stream?: 'oil' | 'gas';
    fit: DeclineFit;
    forecast: Forecast;
}

export interface EconomicMetrics {
    NPV: number;
    ROI: number;
    Payout_Months: number;
    EUR: number;
    EUR_Oil?: number;
    EUR_Gas?: number;
}

export interface FilterOptions {
    formations: string[];
    well_types: string[];
    slants: string[];
}

export interface FilterParams {
    limit?: number;
    skip?: number;
    hasProduction?: boolean;
    search?: string;
    formation?: string;
    wellType?: string;
    slant?: string;
}

export interface WellfileResponse {
    primary_url: string;
    fallback_url: string;
}

export const getFilterOptions = async (): Promise<FilterOptions> => {
    const response = await api.get<FilterOptions>('/filters');
    return response.data;
};

export const getWells = async (params: FilterParams = {}): Promise<Well[]> => {
    const { limit = 100, skip = 0, hasProduction = false, search, formation, wellType, slant } = params;
    const queryParams = new URLSearchParams({
        limit: limit.toString(),
        skip: skip.toString(),
        has_production: hasProduction.toString(),
    });

    if (search) queryParams.append('search', search);
    if (formation) queryParams.append('formation', formation);
    if (wellType) queryParams.append('well_type', wellType);
    if (slant) queryParams.append('slant', slant);

    const response = await api.get<Well[]>(`/wells?${queryParams.toString()}`);
    return response.data;
};

export const getWellProduction = async (apiNumber: string): Promise<ProductionRecord[]> => {
    const response = await api.get<ProductionRecord[]>(`/wells/${apiNumber}/production`);
    return response.data;
};

export const fitDecline = async (apiNumber: string): Promise<DeclineResponse> => {
    const response = await api.post<DeclineResponse>(`/wells/${apiNumber}/decline?method=auto`);
    return response.data;
}

export const runEconomics = async (
    apiNumber: string,
    oilPrice: number,
    capex: number,
    opex: number,
    discountRate: number,
    abandonmentRate: number,
    gasPrice: number = 2.5
): Promise<EconomicMetrics> => {
    const response = await api.post<EconomicMetrics>(`/wells/${apiNumber}/economics`, null, {
        params: {
            oil_price: oilPrice,
            gas_price: gasPrice,
            capex: capex,
            opex: opex,
            discount_rate: discountRate,
            abandonment_rate_daily: abandonmentRate
        }
    });
    return response.data;
};

export const getWellfileUrl = async (apiNumber: string): Promise<WellfileResponse> => {
    const response = await api.get<WellfileResponse>(`/wells/${apiNumber}/wellfile`);
    return response.data;
};

// --- Wellfile Analysis Agent Types ---

export interface CompletionSpecs {
    api_number: string;
    well_name?: string;
    tvd_ft?: number;
    md_ft?: number;
    lateral_length_ft?: number;
    total_clean_fluid_bbls?: number;
    total_proppant_lbs?: number;
    max_treating_pressure_psi?: number;
    casing_intermediate_depth_ft?: number;
}

export interface IpFlowTest {
    test_duration_hrs?: number;
    oil_rate_24hr_bbls?: number;
    gas_rate_24hr_mcf?: number;
    water_rate_24hr_bbls?: number;
    choke_size_inches?: number;
    flowing_tubing_pressure_psi?: number;
    shut_in_tubing_pressure_psi?: number;
    test_method?: string;
}

export interface Perforation {
    top_md_ft?: number;
    bottom_md_ft?: number;
    shots_per_ft?: number;
    gun_charge_diameter_in?: number;
    gun_type?: string;
    phase_angle_deg?: number;
    formation_name?: string;
    status?: string;
}

export interface StimulationStage {
    treatment_type?: string;
    stage_number?: number;
    fluid_volume_bbls?: number;
    chemical_additives?: string;
    diverter_specs?: string;
    max_treating_pressure_psi?: number;
    avg_treating_pressure_psi?: number;
    injection_rate_bpm?: number;
    isip_psi?: number;
}

export interface DownholeTubulars {
    tubing_od_in?: number;
    tubing_weight_lbs_ft?: number;
    tubing_grade?: string;
    thread_type?: string;
    eot_depth_ft?: number;
    seating_nipple_depth_ft?: number;
    tubing_anchor_catcher_depth_ft?: number;
    applied_pretension_lbs?: number;
}

export interface CompletionStimulationData {
    well_name?: string;
    tvd_ft?: number;
    md_ft?: number;
    lateral_length_ft?: number;
    total_clean_fluid_bbls?: number;
    total_proppant_lbs?: number;
    max_treating_pressure_psi?: number;
    casing_intermediate_depth_ft?: number;
    ip_flow_test?: IpFlowTest;
    perforations?: Perforation[];
    stimulation_stages?: StimulationStage[];
    downhole_tubulars?: DownholeTubulars;
}

export interface FormationTop {
    formation_name?: string;
    md_ft?: number;
    tvd_ft?: number;
    subsea_elevation_ft?: number;
    pick_source?: string;
}

export interface HydrocarbonShow {
    depth_from_ft?: number;
    depth_to_ft?: number;
    peak_gas_units?: number;
    baseline_gas_units?: number;
    c1_ppm?: number;
    c2_ppm?: number;
    c3_ppm?: number;
    c4_ppm?: number;
    c5_ppm?: number;
    fluorescence?: string;
    cut?: string;
    lithology_description?: string;
}

export interface GeologyData {
    formation_tops?: FormationTop[];
    hydrocarbon_shows?: HydrocarbonShow[];
}

export interface CasingString {
    string_type?: string;
    hole_size_in?: number;
    casing_od_in?: number;
    nominal_weight_lbs_ft?: number;
    steel_grade?: string;
    connection_type?: string;
    setting_depth_ft?: number;
    burst_rating_psi?: number;
    collapse_rating_psi?: number;
}

export interface CementOperation {
    slurry_volume_sacks?: number;
    slurry_volume_bbls?: number;
    lead_tail_formulation?: string;
    slurry_density_ppg?: number;
    additives?: string;
    displacement_volume_bbls?: number;
    bump_pressure_psi?: number;
    surface_return_volume_bbls?: number;
}

export interface MultiStageTool {
    stage_tool_depth_ft?: number;
    opening_pressure_psi?: number;
    closing_pressure_psi?: number;
    isolation_interval_from_ft?: number;
    isolation_interval_to_ft?: number;
}

export interface CementEvaluation {
    logged_toc_ft?: number;
    verification_method?: string;
    bond_assessment?: string;
}

export interface CasingCementData {
    casing_program?: CasingString[];
    cementing_operations?: CementOperation[];
    multi_stage_tools?: MultiStageTool[];
    cement_evaluation?: CementEvaluation;
}

export interface DrillingFluidParams {
    depth_ft?: number;
    mud_type?: string;
    mud_weight_ppg?: number;
    funnel_viscosity_sec?: number;
    fluid_loss_cc?: number;
    chlorides_ppm?: number;
    oil_water_ratio?: string;
}

export interface BitRun {
    bit_number?: number;
    bit_size_in?: number;
    manufacturer?: string;
    iadc_code?: string;
    cutter_type?: string;
    depth_in_ft?: number;
    depth_out_ft?: number;
    rotating_hours?: number;
    footage_drilled_ft?: number;
    avg_rop_ft_per_hr?: number;
}

export interface WellboreEvent {
    event_type?: string;
    depth_ft?: number;
    description?: string;
    treatment_type?: string;
}

export interface DrillingData {
    drilling_fluid_params?: DrillingFluidParams[];
    bit_runs?: BitRun[];
    wellbore_events?: WellboreEvent[];
}

export interface WellfileExtractionPayload {
    completion_stimulation?: CompletionStimulationData;
    geology?: GeologyData;
    casing_cement?: CasingCementData;
    drilling?: DrillingData;
}

export interface ProductionSummary {
    total_months: number;
    peak_oil_bbls: number;
    peak_gas_mcf: number;
    eur_boe?: number;
    dca_method?: string;
}

export interface WellfileAnalysisResponse {
    api_number: string;
    extraction_status: string;
    cache_hit: boolean;
    completion_specs?: CompletionSpecs;
    production_summary?: ProductionSummary;
    proppant_intensity_lbs_per_ft?: number;
    fluid_intensity_bbls_per_ft?: number;
    well_name?: string;
    wellfile_data?: WellfileExtractionPayload;
}

export const analyzeWellfile = async (apiNumber: string): Promise<WellfileAnalysisResponse> => {
    const response = await api.post<WellfileAnalysisResponse>('/agent/wellfile', {
        api_number: apiNumber,
    });
    return response.data;
};

// ── Stimulation Panel Types ──

export interface ProppantBreakdown {
    silica_lbs?: number;
    resin_coated_lbs?: number;
    ceramic_lbs?: number;
    diverter_lbs?: number;
    other_lbs?: number;
}

export interface AdditiveProfile {
    friction_reducer_max_pct?: number;
    scale_inhibitor_max_pct?: number;
    biocide_max_pct?: number;
    crosslinker_max_pct?: number;
    surfactant_max_pct?: number;
}

export interface GasComponent {
    type: string;
    volume_scf?: number;
    mass_lbs?: number;
    liquid_bbl?: number;
}

export interface ProvenanceTag {
    source: string;
    field_name: string;
    original_value?: number;
    original_unit?: string;
}

export interface SourceView {
    total_clean_fluid_bbls?: number;
    total_proppant_lbs?: number;
    total_acid_gal?: number;
    proppant_concentration_ppa?: number;
    max_treating_pressure_psi?: number;
    tvd_ft?: number;
    provenance: ProvenanceTag[];
}

export interface VarianceReport {
    fluid_volume_delta_pct?: number;
    proppant_mass_delta_pct?: number;
    acid_volume_delta_pct?: number;
    status: string;
    stage_resolution_note?: string;
}

export interface SanityFinding {
    rule: string;
    severity: string;
    message: string;
    raw_value?: number;
    corrected_value?: number;
    corrected_unit?: string;
    note?: string;
}

export interface ReconciledStimulationResponse {
    api_number: string;
    well_name?: string;
    treatment_class?: string;
    total_clean_fluid_bbls?: number;
    total_proppant_lbs?: number;
    total_acid_gal?: number;
    proppant_concentration_ppa?: number;
    base_fluid_type?: string;
    proppant_breakdown?: ProppantBreakdown;
    additives?: AdditiveProfile;
    gas_components: GasComponent[];
    net_perforated_ft?: number;
    acid_intensity_gal_per_ft?: number;
    foam_quality_pct?: number;
    glr_scf_per_bbl?: number;
    max_treating_pressure_psi?: number;
    state_source: SourceView;
    fracfocus_source: SourceView;
    variance?: VarianceReport;
    sanity_findings: SanityFinding[];
    badge: string;
}

export const getReconciledStimulation = async (apiNumber: string): Promise<ReconciledStimulationResponse> => {
    const response = await api.get<ReconciledStimulationResponse>(
        `/wells/${apiNumber}/stimulation`
    );
    return response.data;
};

export const setStimulationOverride = async (apiNumber: string, field: string, value: number, note?: string): Promise<{status: string}> => {
    const response = await api.post(`/wells/${apiNumber}/stimulation/override`, {
        api_number: apiNumber,
        field,
        value,
        note,
    });
    return response.data;
};

// ── Diagnostics Types ──

export interface DiagnosticsResponse {
    api_number: string;
    well_name?: string;
    extraction_status: string;
    sections_extracted: string[];
    stress?: {
        sigma_hmin_psi?: number;
        stress_gradient_psi_per_ft?: number;
        leakoff_type?: string;
        friction_split?: {
            closure_pressure_psi?: number;
            perf_friction_coef?: number;
            nwb_tortuosity_coef?: number;
        };
    };
    water_chemistry?: {
        stiff_davis_caco3_si?: number;
        skillman_mcdonald_caso4?: number;
        barium_sulfate_si?: number;
        rw_ohm_m_77F?: number;
        scale_risk?: string;
    };
    pvt?: {
        gas_specific_gravity?: number;
        btu_scf?: number;
        oil_viscosity_cp?: number;
        bubble_point_psi?: number;
    };
    flowback?: {
        load_recovery_pct?: number;
        load_recovery_assessment?: { risk: string; message: string };
        proppant_flowback?: Array<{ volume_bbls: number; mesh_size: string; risk: string; note: string }>;
    };
    survey?: {
        max_dls_deg_per_100ft?: number;
        lateral_max_dls_deg_per_100ft?: number;
        tortuosity_hotspots?: Array<{ md_ft: number; dls_deg_per_100ft: number; note: string }>;
        survey_points?: Array<{ md_ft: number; inclination_deg: number; azimuth_deg: number; tvd_ft?: number; dls_deg_per_100ft?: number }>;
    };
}

export const getDiagnostics = async (apiNumber: string): Promise<DiagnosticsResponse> => {
    const response = await api.get<DiagnosticsResponse>(`/wells/${apiNumber}/diagnostics`);
    return response.data;
};

// ── Interference Types ──

export interface InterferenceNeighbor {
    api_number: string;
    well_name?: string;
    distance_ft?: number;
    azimuth_deg?: number;
    age_days?: number;
    parent_ratio_pct?: number;
    interference_index?: number;
    risk?: string;
    note?: string;
}

export interface InterferenceResponse {
    api_number: string;
    well_name?: string;
    analyzed: boolean;
    overall_risk?: string;
    message?: string;
    neighbors: InterferenceNeighbor[];
}

export const getInterference = async (apiNumber: string): Promise<InterferenceResponse> => {
    const response = await api.get<InterferenceResponse>(`/wells/${apiNumber}/interference`);
    return response.data;
};
