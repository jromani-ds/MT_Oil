/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState } from 'react';
import type { DiagnosticsResponse, InterferenceResponse } from '../api/client';
import { getDiagnostics, getInterference } from '../api/client';
import {
    Activity, Beaker, Thermometer, Droplets, Map, Radio, Loader2, AlertTriangle, ChevronDown, ChevronUp,
} from 'lucide-react';
import { formatCompactNumber } from '../utils/format';

interface DiagnosticsPanelProps {
    apiNumber: string | null;
    selectedWell: any | null;
}

type TabId = 'stress' | 'water' | 'pvt' | 'flowback' | 'survey' | 'interference';

const TABS: { id: TabId; label: string; icon: typeof Activity }[] = [
    { id: 'stress', label: 'Stress & DFIT', icon: Activity },
    { id: 'water', label: 'Water & Scale', icon: Beaker },
    { id: 'pvt', label: 'PVT', icon: Thermometer },
    { id: 'flowback', label: 'Flowback', icon: Droplets },
    { id: 'survey', label: 'Survey', icon: Map },
    { id: 'interference', label: 'Interference', icon: Radio },
];

// ── formatting helpers ──────────────────────────────────────────────

function fmt(value?: number | null): string {
    if (value === undefined || value === null) return '—';
    return formatCompactNumber(Math.round(value));
}

function fmtTwoDecimal(value?: number | null): string {
    if (value === undefined || value === null) return '—';
    return value.toFixed(2);
}

function fmtThreeDecimal(value?: number | null): string {
    if (value === undefined || value === null) return '—';
    return value.toFixed(3);
}

function fmtPsi(value?: number | null): string {
    if (value === undefined || value === null) return '—';
    return `${fmt(value)} psi`;
}

function fmtFeet(value?: number | null): string {
    if (value === undefined || value === null) return '—';
    return `${fmt(value)} ft`;
}

function fmtPct(value?: number | null): string {
    if (value === undefined || value === null) return '—';
    return `${value.toFixed(1)}%`;
}

function fmtString(value?: string | null): string {
    if (!value) return '—';
    return value;
}

// ── UI sub-components ───────────────────────────────────────────────

function ParamCard({ label, value }: { label: string; value: string }) {
    return (
        <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">{label}</p>
            <p className="text-lg font-mono font-bold text-gray-800">{value}</p>
        </div>
    );
}

function RiskBadge({ risk }: { risk?: string }) {
    const r = (risk || '').toLowerCase();
    const cls =
        r === 'low' ? 'bg-green-100 text-green-700' :
        r === 'medium' || r === 'moderate' ? 'bg-amber-100 text-amber-700' :
        r === 'high' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600';
    return (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${cls}`}>
            {risk || 'N/A'}
        </span>
    );
}

interface CollapsibleSectionProps {
    title: string;
    accentClass: string;
    defaultOpen?: boolean;
    children: React.ReactNode;
}

function CollapsibleSection({ title, accentClass, defaultOpen = false, children }: CollapsibleSectionProps) {
    const [open, setOpen] = useState(defaultOpen);
    return (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
            <button
                onClick={() => setOpen(!open)}
                className={`w-full flex items-center justify-between px-4 py-3 text-left ${accentClass} transition-colors`}
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

// ── section renderers ───────────────────────────────────────────────

function StressTab({ data }: { data: DiagnosticsResponse['stress'] }) {
    if (!data) return <p className="text-sm text-gray-400 italic">No stress / DFIT data</p>;
    const fs = data.friction_split;
    return (
        <div className="space-y-5">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <ParamCard label="σhmin (psi)" value={fmtPsi(data.sigma_hmin_psi)} />
                <ParamCard label="Stress Gradient (psi/ft)" value={fmtThreeDecimal(data.stress_gradient_psi_per_ft)} />
                <ParamCard label="Leakoff Type" value={fmtString(data.leakoff_type)} />
            </div>
            {fs && (
                <div className="mt-2">
                    <CollapsibleSection title="Friction Split" accentClass="bg-indigo-50 text-indigo-800 hover:bg-indigo-100" defaultOpen={false}>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            <ParamCard label="Closure Pressure (psi)" value={fmtPsi(fs.closure_pressure_psi)} />
                            <ParamCard label="Perf Friction Coef" value={fmtTwoDecimal(fs.perf_friction_coef)} />
                            <ParamCard label="NWB Tortuosity Coef" value={fmtTwoDecimal(fs.nwb_tortuosity_coef)} />
                        </div>
                    </CollapsibleSection>
                </div>
            )}
        </div>
    );
}

function WaterTab({ data }: { data: DiagnosticsResponse['water_chemistry'] }) {
    if (!data) return <p className="text-sm text-gray-400 italic">No water chemistry / scale data</p>;
    return (
        <div className="space-y-5">
            <div className="flex items-center gap-3 mb-1">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Scale Risk</span>
                <RiskBadge risk={data.scale_risk} />
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <ParamCard label="Stiff-Davis CaCO₃ SI" value={fmtTwoDecimal(data.stiff_davis_caco3_si)} />
                <ParamCard label="Skillman-McDonald CaSO₄" value={fmtTwoDecimal(data.skillman_mcdonald_caso4)} />
                <ParamCard label="BaSO₄ SI" value={fmtTwoDecimal(data.barium_sulfate_si)} />
                <ParamCard label="Rw @ 77°F (Ω·m)" value={fmtTwoDecimal(data.rw_ohm_m_77F)} />
            </div>
        </div>
    );
}

function PvtTab({ data }: { data: DiagnosticsResponse['pvt'] }) {
    if (!data) return <p className="text-sm text-gray-400 italic">No PVT data</p>;
    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <ParamCard label="Gas Specific Gravity" value={fmtThreeDecimal(data.gas_specific_gravity)} />
            <ParamCard label="Heating Value (BTU/scf)" value={fmt(data.btu_scf)} />
            <ParamCard label="Oil Viscosity (cP)" value={fmtTwoDecimal(data.oil_viscosity_cp)} />
            <ParamCard label="Bubble Point (psi)" value={fmtPsi(data.bubble_point_psi)} />
        </div>
    );
}

function FlowbackTab({ data }: { data: DiagnosticsResponse['flowback'] }) {
    if (!data) return <p className="text-sm text-gray-400 italic">No flowback data</p>;
    const assess = data.load_recovery_assessment;
    const pf = data.proppant_flowback || [];
    return (
        <div className="space-y-5">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <ParamCard label="Load Recovery" value={fmtPct(data.load_recovery_pct)} />
                {assess && (
                    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                        <div className="flex items-center gap-2 mb-1">
                            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Load Recovery Assessment</p>
                            <RiskBadge risk={assess.risk} />
                        </div>
                        <p className="text-sm text-gray-700">{fmtString(assess.message)}</p>
                    </div>
                )}
            </div>
            {pf.length > 0 && (
                <div className="mt-2">
                    <CollapsibleSection title={`Proppant Flowback (${pf.length})`} accentClass="bg-orange-50 text-orange-800 hover:bg-orange-100" defaultOpen={false}>
                        <div className="space-y-2">
                            {pf.map((p, i) => (
                                <div key={i} className="bg-gray-50 rounded px-3 py-2 border border-gray-100 flex flex-col sm:flex-row sm:items-center gap-2">
                                    <span className="text-sm font-mono font-bold text-gray-800">{fmt(p.volume_bbls)} bbls</span>
                                    <span className="text-sm text-gray-600">· {fmtString(p.mesh_size)} mesh</span>
                                    <span className="flex items-center gap-2 text-sm text-gray-600">
                                        · <RiskBadge risk={p.risk} />
                                    </span>
                                    {p.note && <span className="text-xs text-gray-400 italic sm:ml-auto">{p.note}</span>}
                                </div>
                            ))}
                        </div>
                    </CollapsibleSection>
                </div>
            )}
        </div>
    );
}

function SurveyTab({ data }: { data: DiagnosticsResponse['survey'] }) {
    if (!data) return <p className="text-sm text-gray-400 italic">No survey data</p>;
    const hotspots = data.tortuosity_hotspots || [];
    return (
        <div className="space-y-5">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <ParamCard label="Max DLS (°/100ft)" value={fmtTwoDecimal(data.max_dls_deg_per_100ft)} />
                <ParamCard label="Lateral Max DLS (°/100ft)" value={fmtTwoDecimal(data.lateral_max_dls_deg_per_100ft)} />
                <ParamCard label="Tortuosity Hotspots" value={String(hotspots.length)} />
            </div>
            {hotspots.length > 0 && (
                <div className="mt-2">
                    <CollapsibleSection title={`Tortuosity Hotspots (${hotspots.length})`} accentClass="bg-red-50 text-red-800 hover:bg-red-100" defaultOpen={false}>
                        <div className="overflow-x-auto">
                            <table className="w-full text-xs font-mono border-collapse">
                                <thead>
                                    <tr className="border-b border-gray-200">
                                        <th className="text-left px-2 py-1.5 font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap">MD (ft)</th>
                                        <th className="text-left px-2 py-1.5 font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap">DLS (°/100ft)</th>
                                        <th className="text-left px-2 py-1.5 font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap">Note</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {hotspots.map((h, i) => (
                                        <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                                            <td className="px-2 py-1.5 text-gray-700">{fmtFeet(h.md_ft)}</td>
                                            <td className="px-2 py-1.5 text-gray-700">{fmtTwoDecimal(h.dls_deg_per_100ft)}</td>
                                            <td className="px-2 py-1.5 text-gray-700">{fmtString(h.note)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </CollapsibleSection>
                </div>
            )}
        </div>
    );
}

function InterferenceSection({ apiNumber }: { apiNumber: string }) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(false);
    const [data, setData] = useState<InterferenceResponse | null>(null);

    const run = async () => {
        setError(false);
        setLoading(true);
        try {
            const res = await getInterference(apiNumber);
            setData(res);
        } catch {
            setError(true);
        } finally {
            setLoading(false);
        }
    };

    if (loading && !data) {
        return (
            <div className="flex items-center justify-center py-10 text-gray-400">
                <Loader2 className="w-8 h-8 animate-spin opacity-40" />
            </div>
        );
    }

    if (error) {
        return (
            <div className="text-center py-10 text-gray-400">
                <AlertTriangle className="w-12 h-12 mx-auto mb-3 opacity-20" />
                <p className="text-sm mb-4">Could not analyze interference for this well.</p>
                <button
                    onClick={run}
                    disabled={loading}
                    className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Loader2 className="w-4 h-4" />}
                    Retry
                </button>
            </div>
        );
    }

    if (!data) {
        return (
            <div className="text-center py-10 text-gray-400">
                <Radio className="w-12 h-12 mx-auto mb-3 opacity-20" />
                <p className="text-sm mb-4">Run interference analysis to check spacing, completion timing, and parent-child risk.</p>
                <button
                    onClick={run}
                    disabled={loading}
                    className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Radio className="w-4 h-4" />}
                    Run Interference Analysis
                </button>
            </div>
        );
    }

    if (!data.analyzed || !data.neighbors || data.neighbors.length === 0) {
        return (
            <div className="text-center py-10 text-gray-400">
                <Radio className="w-12 h-12 mx-auto mb-3 opacity-20" />
                <p className="text-sm">{data.message || 'No interference analysis available for this well.'}</p>
            </div>
        );
    }

    return (
        <div className="space-y-5">
            <div className="flex items-center gap-3">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Overall Risk</span>
                <RiskBadge risk={data.overall_risk} />
            </div>
            <div className="overflow-x-auto">
                <table className="w-full text-xs font-mono border-collapse">
                    <thead>
                        <tr className="border-b border-gray-200">
                            <th className="text-left px-2 py-1.5 font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap">API</th>
                            <th className="text-left px-2 py-1.5 font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap">Distance</th>
                            <th className="text-left px-2 py-1.5 font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap">Azimuth</th>
                            <th className="text-left px-2 py-1.5 font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap">Age</th>
                            <th className="text-left px-2 py-1.5 font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap">Parent Ratio</th>
                            <th className="text-left px-2 py-1.5 font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap">Index</th>
                            <th className="text-left px-2 py-1.5 font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap">Risk</th>
                            <th className="text-left px-2 py-1.5 font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap">Note</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.neighbors.map((n, i) => (
                            <tr key={n.api_number ?? i} className="border-b border-gray-100 hover:bg-gray-50">
                                <td className="px-2 py-1.5 text-gray-700">{fmtString(n.api_number)}</td>
                                <td className="px-2 py-1.5 text-gray-700">{n.distance_ft != null ? `${fmt(n.distance_ft)} ft` : '—'}</td>
                                <td className="px-2 py-1.5 text-gray-700">{n.azimuth_deg != null ? `${fmt(n.azimuth_deg)}°` : '—'}</td>
                                <td className="px-2 py-1.5 text-gray-700">{n.age_days != null ? `${fmt(n.age_days)} d` : '—'}</td>
                                <td className="px-2 py-1.5 text-gray-700">{n.parent_ratio_pct != null ? `${n.parent_ratio_pct.toFixed(1)}%` : '—'}</td>
                                <td className="px-2 py-1.5 text-gray-700">{n.interference_index != null ? fmtTwoDecimal(n.interference_index) : '—'}</td>
                                <td className="px-2 py-1.5"><RiskBadge risk={n.risk} /></td>
                                <td className="px-2 py-1.5 text-gray-700">{fmtString(n.note)}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

// ── Main component ──────────────────────────────────────────────────

export function DiagnosticsPanel({ apiNumber, selectedWell }: DiagnosticsPanelProps) {
    const [tab, setTab] = useState<TabId>('stress');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(false);
    const [data, setData] = useState<DiagnosticsResponse | null>(null);

    const run = async () => {
        if (!selectedWell || !apiNumber) return;
        setError(false);
        setLoading(true);
        try {
            const res = await getDiagnostics(apiNumber);
            setData(res);
        } catch {
            setError(true);
            setData(null);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="w-full p-4 sm:p-6 lg:p-8">
                <div className="bg-white rounded-lg shadow-md border-l-4 border-amber-500 p-4 sm:p-6 lg:p-8">
                    {/* Header */}
                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 pb-4 border-b border-gray-200">
                        <div>
                            <h3 className="font-bold text-2xl flex items-center gap-2 text-gray-800">
                                <Activity className="w-8 h-8 text-amber-600" /> Deep Diagnostics
                            </h3>
                            <p className="text-sm text-gray-500 mt-1">Rock mechanics, water chemistry, PVT, flowback & survey analysis</p>
                        </div>
                        <button
                            onClick={run}
                            disabled={loading || !selectedWell}
                            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-amber-600 rounded-lg hover:bg-amber-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Activity className="w-4 h-4" />}
                            {loading ? 'Running…' : 'Run Deep Diagnostics'}
                        </button>
                    </div>

                    {!selectedWell && (
                        <div className="text-center py-14 text-gray-400">
                            <Activity className="w-16 h-16 mx-auto mb-4 opacity-20" />
                            <p className="text-lg">Select a well from the Map tab to run deep diagnostics</p>
                        </div>
                    )}

                    {selectedWell && loading && !data && (
                        <div className="flex items-center justify-center py-14 text-gray-400">
                            <div className="text-center">
                                <Loader2 className="w-16 h-16 mx-auto mb-4 opacity-20 animate-spin" />
                                <p className="text-lg">Running deep diagnostics…</p>
                            </div>
                        </div>
                    )}

                    {selectedWell && !loading && !data && (
                        <div className="text-center py-14 text-gray-400">
                            {error ? (
                                <>
                                    <AlertTriangle className="w-16 h-16 mx-auto mb-4 opacity-20" />
                                    <p className="text-lg mb-2">Could not run deep diagnostics</p>
                                    <p className="text-sm text-gray-400 mb-4">This may be a temporary issue — try again.</p>
                                    <button
                                        onClick={run}
                                        className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-amber-600 rounded-lg hover:bg-amber-700 transition-colors"
                                    >
                                        <Loader2 className="w-4 h-4" />
                                        Retry
                                    </button>
                                </>
                            ) : (
                                <>
                                    <Activity className="w-16 h-16 mx-auto mb-4 opacity-20" />
                                    <p className="text-lg max-w-md mx-auto">
                                        Click 'Run Deep Diagnostics' to analyze rock mechanics, water chemistry, PVT, flowback, survey, and interference
                                    </p>
                                </>
                            )}
                        </div>
                    )}

                    {selectedWell && data && (
                        <>
                            {/* Tabs */}
                            <div className="flex gap-1 mb-6 bg-gray-100 rounded-lg p-1 w-full overflow-x-auto">
                                {TABS.map(({ id, label, icon: Icon }) => (
                                    <button
                                        key={id}
                                        onClick={() => setTab(id)}
                                        className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors whitespace-nowrap ${
                                            tab === id ? 'bg-white text-amber-700 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                                        }`}
                                    >
                                        <Icon className="w-4 h-4" />
                                        {label}
                                    </button>
                                ))}
                            </div>

                            {data.well_name && (
                                <p className="text-sm text-gray-500 mb-4">{data.well_name} · {data.sections_extracted?.length || 0} sections extracted</p>
                            )}

                            {/* Tab content */}
                            {tab === 'stress' && <StressTab data={data.stress} />}
                            {tab === 'water' && <WaterTab data={data.water_chemistry} />}
                            {tab === 'pvt' && <PvtTab data={data.pvt} />}
                            {tab === 'flowback' && <FlowbackTab data={data.flowback} />}
                            {tab === 'survey' && <SurveyTab data={data.survey} />}
                            {tab === 'interference' && <InterferenceSection apiNumber={apiNumber!} />}

                            {/* Loading overlay for re-runs with existing data */}
                            {loading && (
                                <div className="mt-4 flex items-center justify-center gap-2 text-sm text-gray-500">
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    <span>Re-running diagnostics…</span>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
