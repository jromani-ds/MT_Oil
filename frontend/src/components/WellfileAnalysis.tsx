import type { Well, WellfileResponse, WellfileAnalysisResponse } from '../api/client';
import { FileSearch, Loader2, AlertTriangle, CheckCircle, Database } from 'lucide-react';
import { formatCompactNumber, formatVolume } from '../utils/format';
import { KpiCard } from './KpiCard';

interface WellfileAnalysisProps {
    selectedWell: Well | null;
    loading: boolean;
    analysis: WellfileAnalysisResponse | null;
    wellfileUrl: WellfileResponse | null;
}

function formatFeet(value?: number): string {
    if (value === undefined || value === null) return '—';
    return `${formatCompactNumber(Math.round(value))} ft`;
}

function formatBarrels(value?: number): string {
    if (value === undefined || value === null) return '—';
    return formatVolume(value);
}

function formatPounds(value?: number): string {
    if (value === undefined || value === null) return '—';
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M lbs`;
    if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k lbs`;
    return `${Math.round(value)} lbs`;
}

function formatPsi(value?: number): string {
    if (value === undefined || value === null) return '—';
    return `${formatCompactNumber(Math.round(value))} psi`;
}

function formatIntensity(value?: number, unit?: string): string {
    if (value === undefined || value === null) return '—';
    return `${formatCompactNumber(Math.round(value))} ${unit || ''}`;
}

function StatusBadge({ status, cacheHit }: { status: string; cacheHit: boolean }) {
    if (status === 'FAILED_PARSING') {
        return (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
                <AlertTriangle className="w-3 h-3" />
                Extraction Failed
            </span>
        );
    }
    if (cacheHit) {
        return (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
                <Database className="w-3 h-3" />
                Cached
            </span>
        );
    }
    return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
            <CheckCircle className="w-3 h-3" />
            Fresh Extraction
        </span>
    );
}

function ParamCard({ label, value }: { label: string; value: string }) {
    return (
        <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">{label}</p>
            <p className="text-lg font-mono font-bold text-gray-800">{value}</p>
        </div>
    );
}

export function WellfileAnalysis({ selectedWell, loading, analysis, wellfileUrl }: WellfileAnalysisProps) {
    if (!selectedWell) {
        return (
            <div className="flex-1 overflow-y-auto">
                <div className="h-full flex items-center justify-center text-gray-400">
                    <div className="text-center">
                        <FileSearch className="w-16 h-16 mx-auto mb-4 opacity-20" />
                        <p className="text-lg">Select a well from the Map tab to analyze its wellfile</p>
                    </div>
                </div>
            </div>
        );
    }

    if (loading && !analysis) {
        return (
            <div className="flex-1 overflow-y-auto">
                <div className="h-full flex items-center justify-center text-gray-400">
                    <div className="text-center">
                        <Loader2 className="w-16 h-16 mx-auto mb-4 opacity-20 animate-spin" />
                        <p className="text-lg">Analyzing wellfile data...</p>
                    </div>
                </div>
            </div>
        );
    }

    if (!analysis) {
        return (
            <div className="flex-1 overflow-y-auto">
                <div className="h-full flex items-center justify-center text-gray-400">
                    <div className="text-center max-w-md">
                        <FileSearch className="w-16 h-16 mx-auto mb-4 opacity-20" />
                        <p className="text-lg mb-2">No wellfile analysis available</p>
                        <p className="text-sm text-gray-400">Try selecting a different well with production data.</p>
                    </div>
                </div>
            </div>
        );
    }

    const specs = analysis.completion_specs;
    const prod = analysis.production_summary;

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="w-full p-4 sm:p-6 lg:p-8">
                <div className="bg-white rounded-lg shadow-md border-l-4 border-blue-500 p-4 sm:p-6 lg:p-8">
                    {/* Header */}
                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 pb-4 border-b border-gray-200">
                        <div>
                            <h3 className="font-bold text-2xl flex items-center gap-2 text-gray-800">
                                <FileSearch className="w-8 h-8 text-blue-600" /> Wellfile Analysis
                            </h3>
                            {analysis.well_name && (
                                <p className="text-sm text-gray-500 mt-1">{analysis.well_name}</p>
                            )}
                        </div>
                        <div className="flex items-center gap-3">
                            <StatusBadge status={analysis.extraction_status} cacheHit={analysis.cache_hit} />
                            {wellfileUrl && (
                                <a
                                    href={wellfileUrl.primary_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-blue-600 hover:text-blue-800 cursor-pointer"
                                >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                    Download PDF
                                </a>
                            )}
                        </div>
                    </div>

                    {/* Extraction Failed State */}
                    {analysis.extraction_status === 'FAILED_PARSING' && (
                        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
                            <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5 shrink-0" />
                            <div>
                                <p className="font-semibold text-red-800">Extraction Failed</p>
                                <p className="text-sm text-red-600 mt-1">
                                    Could not extract completion data from this wellfile. The PDF may be scanned,
                                    corrupted, or illegible. Try downloading the original PDF to review manually.
                                </p>
                                {wellfileUrl && (
                                    <a
                                        href={wellfileUrl.primary_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center gap-1 mt-2 text-sm font-medium text-red-700 hover:text-red-900 underline"
                                    >
                                        Download Original PDF →
                                    </a>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Completion Parameters */}
                    {specs && (
                        <>
                            <h4 className="text-lg font-semibold text-gray-700 mb-4">
                                Completion Parameters
                            </h4>
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
                                <ParamCard label="True Vertical Depth (TVD)" value={formatFeet(specs.tvd_ft)} />
                                <ParamCard label="Total Measured Depth (MD)" value={formatFeet(specs.md_ft)} />
                                <ParamCard label="Lateral Length" value={formatFeet(specs.lateral_length_ft)} />
                                <ParamCard label="Total Clean Fluid" value={formatBarrels(specs.total_clean_fluid_bbls)} />
                                <ParamCard label="Total Proppant" value={formatPounds(specs.total_proppant_lbs)} />
                                <ParamCard label="Max Treating Pressure" value={formatPsi(specs.max_treating_pressure_psi)} />
                                {specs.casing_intermediate_depth_ft !== undefined && specs.casing_intermediate_depth_ft !== null && (
                                    <ParamCard label="Casing Intermediate Depth" value={formatFeet(specs.casing_intermediate_depth_ft)} />
                                )}
                            </div>

                            {/* Completion Intensity KPIs */}
                            <h4 className="text-lg font-semibold text-gray-700 mb-4">
                                Completion Intensity
                            </h4>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-8">
                                <KpiCard
                                    label="Proppant Intensity"
                                    value={formatIntensity(analysis.proppant_intensity_lbs_per_ft, 'lbs/ft')}
                                    colorScheme="purple"
                                />
                                <KpiCard
                                    label="Fluid Intensity"
                                    value={formatIntensity(analysis.fluid_intensity_bbls_per_ft, 'bbls/ft')}
                                    colorScheme="orange"
                                />
                            </div>
                        </>
                    )}

                    {/* Production Summary */}
                    {prod && prod.total_months > 0 && (
                        <>
                            <h4 className="text-lg font-semibold text-gray-700 mb-4">
                                Production Summary
                            </h4>
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                                <div>
                                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Months on Production</p>
                                    <p className="text-lg font-mono font-bold text-gray-800">{prod.total_months}</p>
                                </div>
                                <div>
                                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Peak Oil (monthly)</p>
                                    <p className="text-lg font-mono font-bold text-gray-800">{formatBarrels(prod.peak_oil_bbls)}</p>
                                </div>
                                <div>
                                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Peak Gas (monthly)</p>
                                    <p className="text-lg font-mono font-bold text-gray-800">{formatCompactNumber(Math.round(prod.peak_gas_mcf))} mcf</p>
                                </div>
                                <div>
                                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">EUR (BOE)</p>
                                    <p className="text-lg font-mono font-bold text-gray-800">
                                        {prod.eur_boe ? formatVolume(prod.eur_boe) : '—'}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">DCA Method</p>
                                    <p className="text-lg font-mono font-bold text-gray-800">
                                        {prod.dca_method ? prod.dca_method.charAt(0).toUpperCase() + prod.dca_method.slice(1) : 'N/A'}
                                    </p>
                                </div>
                            </div>
                        </>
                    )}

                    {/* Loading overlay for subsequent re-analysis */}
                    {loading && (
                        <div className="mt-4 flex items-center justify-center gap-2 text-sm text-gray-500">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span>Re-analyzing...</span>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
