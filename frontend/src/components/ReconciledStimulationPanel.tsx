import { useCallback, useEffect, useState } from 'react';
import type { ReconciledStimulationResponse } from '../api/client';
import { getReconciledStimulation } from '../api/client';
import { CheckCircle, AlertTriangle, XCircle, Loader2, ChevronDown, ChevronUp, Database } from 'lucide-react';
import { formatCompactNumber, formatVolume } from '../utils/format';
import { KpiCard } from './KpiCard';

// ── Types ──

interface ReconciledStimulationPanelProps {
    apiNumber: string;
}

type ViewMode = 'reconciled' | 'state' | 'fracfocus';

// ── Formatting helpers ──

function fmt(value?: number | null): string {
    if (value === undefined || value === null) return '—';
    return formatCompactNumber(Math.round(value));
}

function fmtOneDecimal(value?: number | null): string {
    if (value === undefined || value === null) return '—';
    return value.toFixed(1);
}

function fmtPct(value?: number | null): string {
    if (value === undefined || value === null) return '—';
    const sign = value > 0 ? '+' : '';
    return `${sign}${value.toFixed(1)}%`;
}

function fmtPounds(value?: number | null): string {
    if (value === undefined || value === null) return '—';
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M lbs`;
    if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k lbs`;
    return `${Math.round(value)} lbs`;
}

function fmtBarrels(value?: number | null): string {
    if (value === undefined || value === null) return '—';
    return formatVolume(value);
}

function fmtGallons(value?: number | null): string {
    if (value === undefined || value === null) return '—';
    if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k gal`;
    return `${Math.round(value)} gal`;
}

function fmtString(value?: string | null): string {
    if (!value) return '—';
    return value;
}

// ── Sub-components ──

function BadgeIcon({ badge }: { badge: string }) {
    switch (badge) {
        case 'good':
        case 'pass':
            return (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
                    <CheckCircle className="w-4 h-4" />
                    {badge === 'good' ? 'Good' : 'Pass'}
                </span>
            );
        case 'warning':
            return (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
                    <AlertTriangle className="w-4 h-4" />
                    Warning
                </span>
            );
        case 'fail':
        case 'error':
            return (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
                    <XCircle className="w-4 h-4" />
                    {badge === 'fail' ? 'Fail' : 'Error'}
                </span>
            );
        default:
            return (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                    {badge}
                </span>
            );
    }
}

function SeverityBadge({ severity }: { severity: string }) {
    const s = severity.toLowerCase();
    if (s === 'info' || s === 'pass') {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
                <CheckCircle className="w-3 h-3" />
                {severity}
            </span>
        );
    }
    if (s === 'warning') {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
                <AlertTriangle className="w-3 h-3" />
                Warning
            </span>
        );
    }
    if (s === 'error' || s === 'fail') {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
                <XCircle className="w-3 h-3" />
                {severity}
            </span>
        );
    }
    return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
            {severity}
        </span>
    );
}

function VarianceStatusBadge({ status }: { status: string }) {
    const s = status.toLowerCase();
    if (s === 'match' || s === 'pass') {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
                <CheckCircle className="w-3 h-3" />
                Match
            </span>
        );
    }
    if (s === 'minor' || s === 'warning') {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
                <AlertTriangle className="w-3 h-3" />
                Minor Variance
            </span>
        );
    }
    if (s === 'major' || s === 'fail') {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
                <XCircle className="w-3 h-3" />
                Major Variance
            </span>
        );
    }
    return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
            {status}
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

function CollapsibleSection({ title, defaultOpen = false, children }: { title: string; defaultOpen?: boolean; children: React.ReactNode }) {
    const [open, setOpen] = useState(defaultOpen);
    return (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
            <button
                onClick={() => setOpen(!open)}
                className="w-full flex items-center justify-between px-4 py-3 text-left bg-blue-50 text-blue-800 hover:bg-blue-100 transition-colors"
            >
                <div className="flex items-center gap-2">
                    {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    <span className="font-semibold text-sm">{title}</span>
                </div>
            </button>
            {open && <div className="p-4 bg-white">{children}</div>}
        </div>
    );
}

function ObjectCard({ fields }: { fields: { label: string; value: string }[] }) {
    const nonEmpty = fields.filter(f => f.value !== '—');
    if (nonEmpty.length === 0) return <p className="text-sm text-gray-400 italic">No data available</p>;
    return (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
            {nonEmpty.map((f, i) => (
                <div key={i} className="bg-gray-50 rounded px-3 py-2 border border-gray-100">
                    <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">{f.label}</p>
                    <p className="text-sm font-mono font-bold text-gray-800 truncate">{f.value}</p>
                </div>
            ))}
        </div>
    );
}

function SourceComparison({ label, reconciled, stateVal, ffVal, unit }: { label: string; reconciled?: number | null; stateVal?: number | null; ffVal?: number | null; unit: string }) {
    const fmtFn = unit === 'bbls' ? fmtBarrels : unit === 'lbs' ? fmtPounds : unit === 'gal' ? fmtGallons : unit === 'ppa' ? fmtOneDecimal : unit === 'psi' ? (v?: number | null) => v != null ? fmt(v) + ' psi' : '—' : fmt;

    const rVal = fmtFn(reconciled);
    const sVal = fmtFn(stateVal);
    const fVal = fmtFn(ffVal);

    return (
        <div className="grid grid-cols-4 gap-3 items-center py-2 border-b border-gray-100 last:border-b-0">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">{label}</p>
            <div className="text-center">
                <p className="text-xs text-gray-400 mb-0.5">Reconciled</p>
                <p className="text-sm font-mono font-bold text-blue-700">{rVal}</p>
            </div>
            <div className="text-center">
                <p className="text-xs text-gray-400 mb-0.5">State</p>
                <p className="text-sm font-mono font-bold text-gray-800">{sVal}</p>
            </div>
            <div className="text-center">
                <p className="text-xs text-gray-400 mb-0.5">FracFocus</p>
                <p className="text-sm font-mono font-bold text-gray-800">{fVal}</p>
            </div>
        </div>
    );
}

// ── Main component ──

export function ReconciledStimulationPanel({ apiNumber }: ReconciledStimulationPanelProps) {
    const [viewMode, setViewMode] = useState<ViewMode>('reconciled');
    const [stimulation, setStimulation] = useState<ReconciledStimulationResponse | null>(null);
    const [loading, setLoading] = useState(true);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const result = await getReconciledStimulation(apiNumber);
            setStimulation(result);
        } catch {
            setStimulation(null);
        } finally {
            setLoading(false);
        }
    }, [apiNumber]);

    useEffect(() => {
        load();
    }, [load]);

    if (loading && !stimulation) {
        return (
            <div className="flex-1 overflow-y-auto">
                <div className="h-full flex items-center justify-center text-gray-400">
                    <div className="text-center">
                        <Loader2 className="w-16 h-16 mx-auto mb-4 opacity-20 animate-spin" />
                        <p className="text-lg">Loading stimulation data...</p>
                    </div>
                </div>
            </div>
        );
    }

    if (!stimulation) {
        return (
            <div className="flex-1 overflow-y-auto">
                <div className="h-full flex items-center justify-center text-gray-400">
                    <div className="text-center max-w-md">
                        <AlertTriangle className="w-16 h-16 mx-auto mb-4 opacity-20" />
                        <p className="text-lg mb-2">No stimulation data available</p>
                        <p className="text-sm text-gray-400">
                            Could not load reconciled stimulation data for this well.
                        </p>
                        <button
                            onClick={load}
                            className="mt-4 inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                        >
                            <Loader2 className="w-4 h-4" />
                            Retry
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    const showReconciled = viewMode === 'reconciled';
    const showState = viewMode === 'state' || viewMode === 'reconciled';
    const showFracFocus = viewMode === 'fracfocus' || viewMode === 'reconciled';

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="w-full p-4 sm:p-6 lg:p-8">
                <div className="bg-white rounded-lg shadow-md border-l-4 border-blue-500 p-4 sm:p-6 lg:p-8">
                    {/* Header */}
                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 pb-4 border-b border-gray-200">
                        <div>
                            <h3 className="font-bold text-2xl flex items-center gap-2 text-gray-800">
                                <Database className="w-8 h-8 text-blue-600" /> Reconciled Stimulation
                            </h3>
                            {stimulation.well_name && (
                                <p className="text-sm text-gray-500 mt-1">{stimulation.well_name}</p>
                            )}
                        </div>
                        <BadgeIcon badge={stimulation.badge} />
                    </div>

                    {/* View Toggle */}
                    <div className="flex gap-1 mb-6 bg-gray-100 rounded-lg p-1 w-fit">
                        {(['reconciled', 'state', 'fracfocus'] as ViewMode[]).map(mode => (
                            <button
                                key={mode}
                                onClick={() => setViewMode(mode)}
                                className={`px-4 py-2 text-sm font-medium rounded-md transition-colors capitalize ${
                                    viewMode === mode
                                        ? 'bg-white text-blue-700 shadow-sm'
                                        : 'text-gray-500 hover:text-gray-700'
                                }`}
                            >
                                {mode === 'reconciled' ? 'Reconciled' : mode === 'state' ? 'State' : 'FracFocus'}
                            </button>
                        ))}
                    </div>

                    {/* KPI Cards */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
                        {showReconciled && (
                            <>
                                <KpiCard
                                    label="Total Clean Fluid"
                                    value={fmtBarrels(stimulation.total_clean_fluid_bbls)}
                                    colorScheme="blue"
                                />
                                <KpiCard
                                    label="Total Proppant"
                                    value={fmtPounds(stimulation.total_proppant_lbs)}
                                    colorScheme="purple"
                                />
                                <KpiCard
                                    label="PPA"
                                    value={fmtOneDecimal(stimulation.proppant_concentration_ppa)}
                                    colorScheme="orange"
                                />
                                <KpiCard
                                    label="Total Acid"
                                    value={fmtGallons(stimulation.total_acid_gal)}
                                    colorScheme="green"
                                />
                                <ParamCard label="Treatment Class" value={fmtString(stimulation.treatment_class)} />
                                <ParamCard label="Base Fluid" value={fmtString(stimulation.base_fluid_type)} />
                            </>
                        )}
                        {showState && !showReconciled && (
                            <>
                                <KpiCard
                                    label="Total Clean Fluid"
                                    value={fmtBarrels(stimulation.state_source.total_clean_fluid_bbls)}
                                    colorScheme="blue"
                                />
                                <KpiCard
                                    label="Total Proppant"
                                    value={fmtPounds(stimulation.state_source.total_proppant_lbs)}
                                    colorScheme="purple"
                                />
                                <KpiCard
                                    label="PPA"
                                    value={fmtOneDecimal(stimulation.state_source.proppant_concentration_ppa)}
                                    colorScheme="orange"
                                />
                                <KpiCard
                                    label="Total Acid"
                                    value={fmtGallons(stimulation.state_source.total_acid_gal)}
                                    colorScheme="green"
                                />
                                <ParamCard label="Max Treating Pressure" value={fmt(stimulation.state_source.max_treating_pressure_psi) + ' psi'} />
                                <ParamCard label="TVD" value={fmt(stimulation.state_source.tvd_ft) + ' ft'} />
                            </>
                        )}
                        {showFracFocus && !showReconciled && (
                            <>
                                <KpiCard
                                    label="Total Clean Fluid"
                                    value={fmtBarrels(stimulation.fracfocus_source.total_clean_fluid_bbls)}
                                    colorScheme="blue"
                                />
                                <KpiCard
                                    label="Total Proppant"
                                    value={fmtPounds(stimulation.fracfocus_source.total_proppant_lbs)}
                                    colorScheme="purple"
                                />
                                <KpiCard
                                    label="PPA"
                                    value={fmtOneDecimal(stimulation.fracfocus_source.proppant_concentration_ppa)}
                                    colorScheme="orange"
                                />
                                <KpiCard
                                    label="Total Acid"
                                    value={fmtGallons(stimulation.fracfocus_source.total_acid_gal)}
                                    colorScheme="green"
                                />
                                <ParamCard label="Max Treating Pressure" value={fmt(stimulation.fracfocus_source.max_treating_pressure_psi) + ' psi'} />
                                <ParamCard label="TVD" value={fmt(stimulation.fracfocus_source.tvd_ft) + ' ft'} />
                            </>
                        )}
                    </div>

                    {/* Derived Metrics */}
                    {showReconciled && (
                        <div className="mb-8">
                            <h4 className="text-lg font-semibold text-gray-700 mb-4">Derived Metrics</h4>
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                                <ParamCard label="Net Perforated Interval" value={stimulation.net_perforated_ft != null ? fmt(stimulation.net_perforated_ft) + ' ft' : '—'} />
                                <ParamCard label="Acid Intensity" value={stimulation.acid_intensity_gal_per_ft != null ? fmtOneDecimal(stimulation.acid_intensity_gal_per_ft) + ' gal/ft' : '—'} />
                                <ParamCard label="Foam Quality" value={stimulation.foam_quality_pct != null ? fmtOneDecimal(stimulation.foam_quality_pct) + '%' : '—'} />
                                <ParamCard label="GLR" value={stimulation.glr_scf_per_bbl != null ? fmt(stimulation.glr_scf_per_bbl) + ' scf/bbl' : '—'} />
                                <ParamCard label="Max Treating Pressure" value={stimulation.max_treating_pressure_psi != null ? fmt(stimulation.max_treating_pressure_psi) + ' psi' : '—'} />
                            </div>
                        </div>
                    )}

                    {/* Proppant Breakdown */}
                    {showReconciled && stimulation.proppant_breakdown && (
                        <CollapsibleSection title="Proppant Breakdown" defaultOpen={false}>
                            <ObjectCard fields={[
                                { label: 'Silica', value: fmtPounds(stimulation.proppant_breakdown.silica_lbs) },
                                { label: 'Resin Coated', value: fmtPounds(stimulation.proppant_breakdown.resin_coated_lbs) },
                                { label: 'Ceramic', value: fmtPounds(stimulation.proppant_breakdown.ceramic_lbs) },
                                { label: 'Diverter', value: fmtPounds(stimulation.proppant_breakdown.diverter_lbs) },
                                { label: 'Other', value: fmtPounds(stimulation.proppant_breakdown.other_lbs) },
                            ].filter(f => f.value !== '—')} />
                        </CollapsibleSection>
                    )}

                    {/* Additives */}
                    {showReconciled && stimulation.additives && (
                        <div className="mt-2">
                            <CollapsibleSection title="Additive Profile" defaultOpen={false}>
                                <ObjectCard fields={[
                                    { label: 'Friction Reducer', value: stimulation.additives.friction_reducer_max_pct != null ? fmtOneDecimal(stimulation.additives.friction_reducer_max_pct) + '%' : '—' },
                                    { label: 'Scale Inhibitor', value: stimulation.additives.scale_inhibitor_max_pct != null ? fmtOneDecimal(stimulation.additives.scale_inhibitor_max_pct) + '%' : '—' },
                                    { label: 'Biocide', value: stimulation.additives.biocide_max_pct != null ? fmtOneDecimal(stimulation.additives.biocide_max_pct) + '%' : '—' },
                                    { label: 'Crosslinker', value: stimulation.additives.crosslinker_max_pct != null ? fmtOneDecimal(stimulation.additives.crosslinker_max_pct) + '%' : '—' },
                                    { label: 'Surfactant', value: stimulation.additives.surfactant_max_pct != null ? fmtOneDecimal(stimulation.additives.surfactant_max_pct) + '%' : '—' },
                                ].filter(f => f.value !== '—')} />
                            </CollapsibleSection>
                        </div>
                    )}

                    {/* Gas Components */}
                    {showReconciled && stimulation.gas_components && stimulation.gas_components.length > 0 && (
                        <div className="mt-2">
                            <CollapsibleSection title={`Gas Components (${stimulation.gas_components.length})`} defaultOpen={false}>
                                <div className="space-y-2">
                                    {stimulation.gas_components.map((gc, i) => (
                                        <div key={i} className="bg-gray-50 rounded px-3 py-2 border border-gray-100">
                                            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">{gc.type}</p>
                                            <div className="flex gap-4 text-sm font-mono text-gray-800">
                                                {gc.volume_scf != null && <span>{fmt(gc.volume_scf)} scf</span>}
                                                {gc.mass_lbs != null && <span>{fmtPounds(gc.mass_lbs)}</span>}
                                                {gc.liquid_bbl != null && <span>{fmtBarrels(gc.liquid_bbl)}</span>}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </CollapsibleSection>
                        </div>
                    )}

                    {/* Source Comparison */}
                    {showReconciled && (
                        <div className="mt-6">
                            <h4 className="text-lg font-semibold text-gray-700 mb-4">Source Comparison</h4>
                            <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
                                <div className="grid grid-cols-3 gap-3 pb-2 border-b border-gray-200 mb-2">
                                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Parameter</p>
                                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider text-center">State</p>
                                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider text-center">FracFocus</p>
                                </div>
                                <SourceComparison label="Clean Fluid" reconciled={stimulation.total_clean_fluid_bbls} stateVal={stimulation.state_source.total_clean_fluid_bbls} ffVal={stimulation.fracfocus_source.total_clean_fluid_bbls} unit="bbls" />
                                <SourceComparison label="Proppant" reconciled={stimulation.total_proppant_lbs} stateVal={stimulation.state_source.total_proppant_lbs} ffVal={stimulation.fracfocus_source.total_proppant_lbs} unit="lbs" />
                                <SourceComparison label="Acid" reconciled={stimulation.total_acid_gal} stateVal={stimulation.state_source.total_acid_gal} ffVal={stimulation.fracfocus_source.total_acid_gal} unit="gal" />
                                <SourceComparison label="PPA" reconciled={stimulation.proppant_concentration_ppa} stateVal={stimulation.state_source.proppant_concentration_ppa} ffVal={stimulation.fracfocus_source.proppant_concentration_ppa} unit="ppa" />
                                <SourceComparison label="Max Pressure" reconciled={stimulation.max_treating_pressure_psi} stateVal={stimulation.state_source.max_treating_pressure_psi} ffVal={stimulation.fracfocus_source.max_treating_pressure_psi} unit="psi" />
                            </div>
                        </div>
                    )}

                    {/* Variance Report */}
                    {showReconciled && stimulation.variance && (
                        <div className="mt-6">
                            <h4 className="text-lg font-semibold text-gray-700 mb-4">Variance Report</h4>
                            <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
                                <div className="flex items-center gap-3 mb-4">
                                    <VarianceStatusBadge status={stimulation.variance.status} />
                                    {stimulation.variance.stage_resolution_note && (
                                        <span className="text-sm text-gray-500 italic">{stimulation.variance.stage_resolution_note}</span>
                                    )}
                                </div>
                                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                                    <ParamCard label="Fluid Volume Delta" value={fmtPct(stimulation.variance.fluid_volume_delta_pct)} />
                                    <ParamCard label="Proppant Mass Delta" value={fmtPct(stimulation.variance.proppant_mass_delta_pct)} />
                                    <ParamCard label="Acid Volume Delta" value={fmtPct(stimulation.variance.acid_volume_delta_pct)} />
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Sanity Findings */}
                    {showReconciled && stimulation.sanity_findings && stimulation.sanity_findings.length > 0 && (
                        <div className="mt-6">
                            <h4 className="text-lg font-semibold text-gray-700 mb-4">
                                Sanity Findings ({stimulation.sanity_findings.length})
                            </h4>
                            <div className="space-y-2">
                                {stimulation.sanity_findings.map((finding, i) => {
                                    const severity = finding.severity.toLowerCase();
                                    let bgClass = 'bg-gray-50 border-gray-200';
                                    let textClass = 'text-gray-800';
                                    if (severity === 'info' || severity === 'pass') {
                                        bgClass = 'bg-green-50 border-green-200';
                                        textClass = 'text-green-800';
                                    } else if (severity === 'warning') {
                                        bgClass = 'bg-amber-50 border-amber-200';
                                        textClass = 'text-amber-800';
                                    } else if (severity === 'error' || severity === 'fail') {
                                        bgClass = 'bg-red-50 border-red-200';
                                        textClass = 'text-red-800';
                                    }
                                    return (
                                        <div key={i} className={`${bgClass} border rounded-lg p-4`}>
                                            <div className="flex items-start justify-between gap-2 mb-2">
                                                <div className="flex items-center gap-2">
                                                    <SeverityBadge severity={finding.severity} />
                                                    <span className={`text-sm font-semibold ${textClass}`}>{finding.rule}</span>
                                                </div>
                                            </div>
                                            <p className="text-sm text-gray-600">{finding.message}</p>
                                            {(finding.raw_value != null || finding.corrected_value != null) && (
                                                <div className="flex gap-4 mt-2 text-xs font-mono text-gray-500">
                                                    {finding.raw_value != null && (
                                                        <span>Raw: {fmt(finding.raw_value)}{finding.corrected_unit ? ` ${finding.corrected_unit}` : ''}</span>
                                                    )}
                                                    {finding.corrected_value != null && (
                                                        <span>Corrected: {fmt(finding.corrected_value)}{finding.corrected_unit ? ` ${finding.corrected_unit}` : ''}</span>
                                                    )}
                                                </div>
                                            )}
                                            {finding.note && (
                                                <p className="text-xs text-gray-400 mt-1 italic">{finding.note}</p>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {/* Provenance */}
                    {showState && !showReconciled && stimulation.state_source.provenance && stimulation.state_source.provenance.length > 0 && (
                        <div className="mt-6">
                            <h4 className="text-lg font-semibold text-gray-700 mb-4">State Data Provenance</h4>
                            <div className="space-y-2">
                                {stimulation.state_source.provenance.map((tag, i) => (
                                    <div key={i} className="bg-gray-50 rounded px-3 py-2 border border-gray-100 text-sm">
                                        <span className="font-semibold text-gray-700">{tag.source}</span>
                                        <span className="text-gray-500"> &middot; {tag.field_name}</span>
                                        {(tag.original_value != null) && (
                                            <span className="text-gray-400 ml-2">
                                                (value: {fmt(tag.original_value)}{tag.original_unit ? ` ${tag.original_unit}` : ''})
                                            </span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {showFracFocus && !showReconciled && stimulation.fracfocus_source.provenance && stimulation.fracfocus_source.provenance.length > 0 && (
                        <div className="mt-6">
                            <h4 className="text-lg font-semibold text-gray-700 mb-4">FracFocus Data Provenance</h4>
                            <div className="space-y-2">
                                {stimulation.fracfocus_source.provenance.map((tag, i) => (
                                    <div key={i} className="bg-gray-50 rounded px-3 py-2 border border-gray-100 text-sm">
                                        <span className="font-semibold text-gray-700">{tag.source}</span>
                                        <span className="text-gray-500"> &middot; {tag.field_name}</span>
                                        {(tag.original_value != null) && (
                                            <span className="text-gray-400 ml-2">
                                                (value: {fmt(tag.original_value)}{tag.original_unit ? ` ${tag.original_unit}` : ''})
                                            </span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Loading overlay */}
                    {loading && (
                        <div className="mt-4 flex items-center justify-center gap-2 text-sm text-gray-500">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span>Refreshing...</span>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
