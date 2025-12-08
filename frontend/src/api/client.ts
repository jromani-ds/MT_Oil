import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

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
    fit: DeclineFit;
    forecast: Forecast;
}

export interface EconomicMetrics {
    NPV: number;
    ROI: number;
    Payout_Months: number;
    EUR: number;
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
    formation?: string;
    wellType?: string;
    slant?: string;
}

export const getFilterOptions = async (): Promise<FilterOptions> => {
    const response = await api.get<FilterOptions>('/filters');
    return response.data;
};

export const getWells = async (params: FilterParams = {}): Promise<Well[]> => {
    const { limit = 100, skip = 0, hasProduction = false, formation, wellType, slant } = params;
    const queryParams = new URLSearchParams({
        limit: limit.toString(),
        skip: skip.toString(),
        has_production: hasProduction.toString(),
    });

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
    oilPrice: number = 70.0,
    capex: number = 6000000.0,
    opex: number = 10.0,
    discountRate: number = 0.10,
    abandonmentRate: number = 5.0
): Promise<EconomicMetrics> => {
    const response = await api.post<EconomicMetrics>(`/wells/${apiNumber}/economics`, null, {
        params: {
            oil_price: oilPrice,
            capex: capex,
            opex: opex,
            discount_rate: discountRate,
            abandonment_rate_daily: abandonmentRate
        }
    });
    return response.data;
}
