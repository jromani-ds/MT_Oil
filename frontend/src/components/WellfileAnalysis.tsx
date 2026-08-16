/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState } from 'react';
import type { Well, WellfileResponse, WellfileAnalysisResponse } from '../api/client';
import { FileSearch, Loader2, AlertTriangle, CheckCircle, Database, ChevronDown, ChevronUp } from 'lucide-react';
import { formatCompactNumber, formatVolume } from '../utils/format';
import { KpiCard } from './KpiCard';

interface WellfileAnalysisProps {
    selectedWell: Well | null;
    loading: boolean;
    analysis: WellfileAnalysisResponse | null;
    wellfileUrl: WellfileResponse | null;
    error: boolean;
    onRetry: () => void;
}

// ── formatting helpers ──────────────────────────────────────────────

function fmt(value?: number | null): string {
    if (value === undefined || value === null) return '—';
    return formatCompactNumber(Math.round(value));
}

function fmtOneDecimal(value?: number | null): string {
    if (value === undefined || value === null) return '—';
    return value.toFixed(1);
}

function fmtFeet(value?: number | null): string {
    if (value === undefined || value === null) return '—';
    return `${formatCompactNumber(Math.round(value))} ft`;
}

function fmtBarrels(value?: number | null): string {
    if (value === undefined || value === null) return '—';
    return formatVolume(value);
}

function fmtPounds(value?: number | null): string {
    if (value === undefined || value === null) return '—';
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M lbs`;
    if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k lbs`;
    return `${Math.round(value)} lbs`;
}

function fmtPsi(value?: number | null): string {
    if (value === undefined || value === null) return '—';
    return `${formatCompactNumber(Math.round(value))} psi`;
}

function fmtBpm(value?: number | null): string {
    if (value === undefined || value === null) return '—';
    return `${value.toFixed(1)} bpm`;
}

function fmtInches(value?: number | null): string {
    if (value === undefined || value === null) return '—';
    return `${value.toFixed(2)} in`;
}

function fmtString(value?: string | null): string {
    if (!value) return '—';
    return value;
}

function fmtIntensity(value?: number, unit?: string): string {
    if (value === undefined || value === null) return '—';
    return `${formatCompactNumber(Math.round(value))} ${unit || ''}`;
}

// ── UI sub-components ───────────────────────────────────────────────

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

interface CollapsibleSectionProps {
    title: string;
    count?: number;
    accentClass: string;
    defaultOpen?: boolean;
    children: React.ReactNode;
}

function CollapsibleSection({ title, count, accentClass, defaultOpen = false, children }: CollapsibleSectionProps) {
    const [open, setOpen] = useState(defaultOpen);

    const hasContent = count === undefined || count > 0;

    return (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
            <button
                onClick={() => setOpen(!open)}
                className={`w-full flex items-center justify-between px-4 py-3 text-left ${accentClass} transition-colors`}
            >
                <div className="flex items-center gap-2">
                    {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    <span className="font-semibold text-sm">{title}</span>
                    {count !== undefined && (
                        <span className={`text-xs font-mono px-1.5 py-0.5 rounded ${hasContent ? 'bg-white/30' : 'bg-gray-200 text-gray-500'}`}>
                            {count}
                        </span>
                    )}
                </div>
            </button>
            {open && (
                <div className="p-4 bg-white">
                    {hasContent ? children : <p className="text-sm text-gray-400 italic">No data available</p>}
                </div>
            )}
        </div>
    );
}

interface DataTableProps {
    columns: { key: string; label: string; render: (row: any) => string }[];
    data: any[];
    keyField: string;
}

function DataTable({ columns, data, keyField }: DataTableProps) {
    if (!data || data.length === 0) return null;
    return (
        <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono border-collapse">
                <thead>
                    <tr className="border-b border-gray-200">
                        {columns.map(col => (
                            <th key={col.key} className="text-left px-2 py-1.5 font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap">
                                {col.label}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {data.map((row, i) => (
                        <tr key={row[keyField] ?? i} className="border-b border-gray-100 hover:bg-gray-50">
                            {columns.map(col => (
                                <td key={col.key} className="px-2 py-1.5 text-gray-700 whitespace-nowrap">
                                    {col.render(row)}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
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

// ── section renderers ───────────────────────────────────────────────

function renderIpFlow(ip: any) {
    if (!ip) return <p className="text-sm text-gray-400 italic">No IP / flow test data</p>;
    return (
        <ObjectCard fields={[
            { label: 'Duration', value: fmt(ip.test_duration_hrs) + ' hrs' },
            { label: 'Oil Rate (24hr)', value: fmtBarrels(ip.oil_rate_24hr_bbls) + '/d' },
            { label: 'Gas Rate (24hr)', value: fmt(ip.gas_rate_24hr_mcf) + ' mcf/d' },
            { label: 'Water Rate (24hr)', value: fmtBarrels(ip.water_rate_24hr_bbls) + '/d' },
            { label: 'Choke', value: fmtInches(ip.choke_size_inches) },
            { label: 'Flowing Tubing P', value: fmtPsi(ip.flowing_tubing_pressure_psi) },
            { label: 'Shut-in Tubing P', value: fmtPsi(ip.shut_in_tubing_pressure_psi) },
            { label: 'Test Method', value: fmtString(ip.test_method) },
        ]} />
    );
}

function renderCompletion1(data: any) {
    if (!data) return null;
    return (
        <div className="space-y-4">
            {data.ip_flow_test && (
                <div>
                    <h5 className="text-sm font-semibold text-gray-600 mb-2">IP / Flow Test</h5>
                    {renderIpFlow(data.ip_flow_test)}
                </div>
            )}
            {data.perforations && data.perforations.length > 0 && (
                <div>
                    <h5 className="text-sm font-semibold text-gray-600 mb-2">Perforations</h5>
                    <DataTable
                        columns={[
                            { key: 'top', label: 'Top MD', render: (r: any) => fmtFeet(r.top_md_ft) },
                            { key: 'bottom', label: 'Bottom MD', render: (r: any) => fmtFeet(r.bottom_md_ft) },
                            { key: 'spf', label: 'SPF', render: (r: any) => fmt(r.shots_per_ft) },
                            { key: 'gun', label: 'Gun/Charge', render: (r: any) => [fmtInches(r.gun_charge_diameter_in), r.gun_type].filter(Boolean).join(' ') || '—' },
                            { key: 'phase', label: 'Phase', render: (r: any) => r.phase_angle_deg ? `${r.phase_angle_deg}°` : '—' },
                            { key: 'fm', label: 'Formation', render: (r: any) => fmtString(r.formation_name) },
                            { key: 'status', label: 'Status', render: (r: any) => fmtString(r.status) },
                        ]}
                        data={data.perforations}
                        keyField="top_md_ft"
                    />
                </div>
            )}
            {data.stimulation_stages && data.stimulation_stages.length > 0 && (
                <div>
                    <h5 className="text-sm font-semibold text-gray-600 mb-2">Stimulation Stages</h5>
                    <DataTable
                        columns={[
                            { key: 'stage', label: 'Stage', render: (r: any) => r.stage_number ?? '—' },
                            { key: 'type', label: 'Type', render: (r: any) => fmtString(r.treatment_type) },
                            { key: 'fluid', label: 'Fluid (bbls)', render: (r: any) => fmt(r.fluid_volume_bbls) },
                            { key: 'maxP', label: 'Max P (psi)', render: (r: any) => fmt(r.max_treating_pressure_psi) },
                            { key: 'avgP', label: 'Avg P (psi)', render: (r: any) => fmt(r.avg_treating_pressure_psi) },
                            { key: 'rate', label: 'Rate (bpm)', render: (r: any) => fmtBpm(r.injection_rate_bpm) },
                            { key: 'isip', label: 'ISIP (psi)', render: (r: any) => fmt(r.isip_psi) },
                            { key: 'chem', label: 'Additives', render: (r: any) => fmtString(r.chemical_additives) },
                            { key: 'dv', label: 'Diverter', render: (r: any) => fmtString(r.diverter_specs) },
                        ]}
                        data={data.stimulation_stages}
                        keyField="stage_number"
                    />
                </div>
            )}
            {data.downhole_tubulars && (
                <div>
                    <h5 className="text-sm font-semibold text-gray-600 mb-2">Downhole Tubulars</h5>
                    <ObjectCard fields={[
                        { label: 'Tubing OD', value: fmtInches(data.downhole_tubulars.tubing_od_in) },
                        { label: 'Weight', value: fmtOneDecimal(data.downhole_tubulars.tubing_weight_lbs_ft) + ' lbs/ft' },
                        { label: 'Grade', value: fmtString(data.downhole_tubulars.tubing_grade) },
                        { label: 'Thread', value: fmtString(data.downhole_tubulars.thread_type) },
                        { label: 'EOT', value: fmtFeet(data.downhole_tubulars.eot_depth_ft) },
                        { label: 'SN', value: fmtFeet(data.downhole_tubulars.seating_nipple_depth_ft) },
                        { label: 'TAC', value: fmtFeet(data.downhole_tubulars.tubing_anchor_catcher_depth_ft) },
                        { label: 'Pretension', value: fmt(data.downhole_tubulars.applied_pretension_lbs) + ' lbs' },
                    ]} />
                </div>
            )}
        </div>
    );
}

function renderGeology(data: any) {
    if (!data) return null;
    return (
        <div className="space-y-4">
            {data.formation_tops && data.formation_tops.length > 0 && (
                <div>
                    <h5 className="text-sm font-semibold text-gray-600 mb-2">Formation Tops</h5>
                    <DataTable
                        columns={[
                            { key: 'fm', label: 'Formation', render: (r: any) => fmtString(r.formation_name) },
                            { key: 'md', label: 'MD (ft)', render: (r: any) => fmtFeet(r.md_ft) },
                            { key: 'tvd', label: 'TVD (ft)', render: (r: any) => fmtFeet(r.tvd_ft) },
                            { key: 'ss', label: 'SS (ft)', render: (r: any) => fmt(r.subsea_elevation_ft) },
                            { key: 'src', label: 'Source', render: (r: any) => fmtString(r.pick_source) },
                        ]}
                        data={data.formation_tops}
                        keyField="formation_name"
                    />
                </div>
            )}
            {data.hydrocarbon_shows && data.hydrocarbon_shows.length > 0 && (
                <div>
                    <h5 className="text-sm font-semibold text-gray-600 mb-2">Hydrocarbon Shows</h5>
                    <DataTable
                        columns={[
                            { key: 'from', label: 'From', render: (r: any) => fmtFeet(r.depth_from_ft) },
                            { key: 'to', label: 'To', render: (r: any) => fmtFeet(r.depth_to_ft) },
                            { key: 'peak', label: 'Peak Gas', render: (r: any) => fmt(r.peak_gas_units) },
                            { key: 'base', label: 'Base Gas', render: (r: any) => fmt(r.baseline_gas_units) },
                            { key: 'c1', label: 'C1', render: (r: any) => fmt(r.c1_ppm) },
                            { key: 'c2', label: 'C2', render: (r: any) => fmt(r.c2_ppm) },
                            { key: 'c3', label: 'C3', render: (r: any) => fmt(r.c3_ppm) },
                            { key: 'c4', label: 'C4', render: (r: any) => fmt(r.c4_ppm) },
                            { key: 'c5', label: 'C5', render: (r: any) => fmt(r.c5_ppm) },
                            { key: 'fluor', label: 'Fluorescence', render: (r: any) => fmtString(r.fluorescence) },
                            { key: 'cut', label: 'Cut', render: (r: any) => fmtString(r.cut) },
                            { key: 'lith', label: 'Lithology', render: (r: any) => fmtString(r.lithology_description) },
                        ]}
                        data={data.hydrocarbon_shows}
                        keyField="depth_from_ft"
                    />
                </div>
            )}
        </div>
    );
}

function renderCasingCement(data: any) {
    if (!data) return null;
    return (
        <div className="space-y-4">
            {data.casing_program && data.casing_program.length > 0 && (
                <div>
                    <h5 className="text-sm font-semibold text-gray-600 mb-2">Casing Program</h5>
                    <DataTable
                        columns={[
                            { key: 'type', label: 'Type', render: (r: any) => fmtString(r.string_type) },
                            { key: 'hole', label: 'Hole (in)', render: (r: any) => fmtInches(r.hole_size_in) },
                            { key: 'od', label: 'OD (in)', render: (r: any) => fmtInches(r.casing_od_in) },
                            { key: 'wt', label: 'Wt (lbs/ft)', render: (r: any) => fmt(r.nominal_weight_lbs_ft) },
                            { key: 'grade', label: 'Grade', render: (r: any) => fmtString(r.steel_grade) },
                            { key: 'conn', label: 'Connection', render: (r: any) => fmtString(r.connection_type) },
                            { key: 'depth', label: 'Set Depth', render: (r: any) => fmtFeet(r.setting_depth_ft) },
                            { key: 'burst', label: 'Burst (psi)', render: (r: any) => fmt(r.burst_rating_psi) },
                            { key: 'coll', label: 'Collapse (psi)', render: (r: any) => fmt(r.collapse_rating_psi) },
                        ]}
                        data={data.casing_program}
                        keyField="string_type"
                    />
                </div>
            )}
            {data.cementing_operations && data.cementing_operations.length > 0 && (
                <div>
                    <h5 className="text-sm font-semibold text-gray-600 mb-2">Cementing Operations</h5>
                    <DataTable
                        columns={[
                            { key: 'sacks', label: 'Sacks', render: (r: any) => fmt(r.slurry_volume_sacks) },
                            { key: 'bbls', label: 'Volume (bbls)', render: (r: any) => fmt(r.slurry_volume_bbls) },
                            { key: 'form', label: 'Formulation', render: (r: any) => fmtString(r.lead_tail_formulation) },
                            { key: 'dens', label: 'Density (ppg)', render: (r: any) => fmtOneDecimal(r.slurry_density_ppg) },
                            { key: 'add', label: 'Additives', render: (r: any) => fmtString(r.additives) },
                            { key: 'disp', label: 'Displ (bbls)', render: (r: any) => fmt(r.displacement_volume_bbls) },
                            { key: 'bump', label: 'Bump (psi)', render: (r: any) => fmt(r.bump_pressure_psi) },
                            { key: 'ret', label: 'Returns (bbls)', render: (r: any) => fmt(r.surface_return_volume_bbls) },
                        ]}
                        data={data.cementing_operations}
                        keyField="slurry_volume_sacks"
                    />
                </div>
            )}
            {data.multi_stage_tools && data.multi_stage_tools.length > 0 && (
                <div>
                    <h5 className="text-sm font-semibold text-gray-600 mb-2">Multi-Stage Tooling</h5>
                    <DataTable
                        columns={[
                            { key: 'depth', label: 'Tool Depth', render: (r: any) => fmtFeet(r.stage_tool_depth_ft) },
                            { key: 'open', label: 'Open (psi)', render: (r: any) => fmt(r.opening_pressure_psi) },
                            { key: 'close', label: 'Close (psi)', render: (r: any) => fmt(r.closing_pressure_psi) },
                            { key: 'isoFrom', label: 'Isolation From', render: (r: any) => fmtFeet(r.isolation_interval_from_ft) },
                            { key: 'isoTo', label: 'Isolation To', render: (r: any) => fmtFeet(r.isolation_interval_to_ft) },
                        ]}
                        data={data.multi_stage_tools}
                        keyField="stage_tool_depth_ft"
                    />
                </div>
            )}
            {data.cement_evaluation && (
                <div>
                    <h5 className="text-sm font-semibold text-gray-600 mb-2">Cement Evaluation</h5>
                    <ObjectCard fields={[
                        { label: 'Logged TOC', value: fmtFeet(data.cement_evaluation.logged_toc_ft) },
                        { label: 'Verification', value: fmtString(data.cement_evaluation.verification_method) },
                        { label: 'Bond Assessment', value: fmtString(data.cement_evaluation.bond_assessment) },
                    ]} />
                </div>
            )}
        </div>
    );
}

function renderDrilling(data: any) {
    if (!data) return null;
    return (
        <div className="space-y-4">
            {data.drilling_fluid_params && data.drilling_fluid_params.length > 0 && (
                <div>
                    <h5 className="text-sm font-semibold text-gray-600 mb-2">Drilling Fluid Parameters</h5>
                    <DataTable
                        columns={[
                            { key: 'depth', label: 'Depth (ft)', render: (r: any) => fmtFeet(r.depth_ft) },
                            { key: 'type', label: 'Mud Type', render: (r: any) => fmtString(r.mud_type) },
                            { key: 'wt', label: 'MW (ppg)', render: (r: any) => fmtOneDecimal(r.mud_weight_ppg) },
                            { key: 'vis', label: 'Vis (sec)', render: (r: any) => fmt(r.funnel_viscosity_sec) },
                            { key: 'fl', label: 'Fluid Loss (cc)', render: (r: any) => fmt(r.fluid_loss_cc) },
                            { key: 'cl', label: 'Cl⁻ (ppm)', render: (r: any) => fmt(r.chlorides_ppm) },
                            { key: 'ow', label: 'O/W Ratio', render: (r: any) => fmtString(r.oil_water_ratio) },
                        ]}
                        data={data.drilling_fluid_params}
                        keyField="depth_ft"
                    />
                </div>
            )}
            {data.bit_runs && data.bit_runs.length > 0 && (
                <div>
                    <h5 className="text-sm font-semibold text-gray-600 mb-2">Bit Runs</h5>
                    <DataTable
                        columns={[
                            { key: 'bit', label: 'Bit #', render: (r: any) => r.bit_number ?? '—' },
                            { key: 'size', label: 'Size (in)', render: (r: any) => fmtInches(r.bit_size_in) },
                            { key: 'mfr', label: 'Mfr', render: (r: any) => fmtString(r.manufacturer) },
                            { key: 'iadc', label: 'IADC', render: (r: any) => fmtString(r.iadc_code) },
                            { key: 'cutter', label: 'Cutter', render: (r: any) => fmtString(r.cutter_type) },
                            { key: 'depthIn', label: 'Depth In', render: (r: any) => fmtFeet(r.depth_in_ft) },
                            { key: 'depthOut', label: 'Depth Out', render: (r: any) => fmtFeet(r.depth_out_ft) },
                            { key: 'hrs', label: 'Rot Hrs', render: (r: any) => fmtOneDecimal(r.rotating_hours) },
                            { key: 'fmg', label: 'Footage', render: (r: any) => fmtFeet(r.footage_drilled_ft) },
                            { key: 'rop', label: 'ROP (ft/hr)', render: (r: any) => fmt(r.avg_rop_ft_per_hr) },
                        ]}
                        data={data.bit_runs}
                        keyField="bit_number"
                    />
                </div>
            )}
            {data.wellbore_events && data.wellbore_events.length > 0 && (
                <div>
                    <h5 className="text-sm font-semibold text-gray-600 mb-2">Wellbore Events</h5>
                    <DataTable
                        columns={[
                            { key: 'type', label: 'Event Type', render: (r: any) => fmtString(r.event_type) },
                            { key: 'depth', label: 'Depth', render: (r: any) => fmtFeet(r.depth_ft) },
                            { key: 'desc', label: 'Description', render: (r: any) => fmtString(r.description) },
                            { key: 'treat', label: 'Treatment', render: (r: any) => fmtString(r.treatment_type) },
                        ]}
                        data={data.wellbore_events}
                        keyField="event_type"
                    />
                </div>
            )}
        </div>
    );
}


// ── Main component ──────────────────────────────────────────────────

export function WellfileAnalysis({ selectedWell, loading, analysis, wellfileUrl, error, onRetry }: WellfileAnalysisProps) {
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
                        <AlertTriangle className="w-16 h-16 mx-auto mb-4 opacity-20" />
                        <p className="text-lg mb-2">
                            {error ? "Could not load wellfile analysis" : "No wellfile analysis available"}
                        </p>
                        <p className="text-sm text-gray-400">
                            {error
                                ? "The analysis could not be completed. This may be a temporary issue — try again."
                                : "Try selecting a different well with production data."}
                        </p>
                        {error && selectedWell && (
                            <button
                                onClick={onRetry}
                                className="mt-4 inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                            >
                                <Loader2 className="w-4 h-4" />
                                Retry Analysis
                            </button>
                        )}
                    </div>
                </div>
            </div>
        );
    }

    const specs = analysis.completion_specs;
    const prod = analysis.production_summary;
    const wf = analysis.wellfile_data;

    const completionCount = (wf?.completion_stimulation?.perforations?.length ?? 0)
        + (wf?.completion_stimulation?.stimulation_stages?.length ?? 0)
        + (wf?.completion_stimulation?.ip_flow_test ? 1 : 0)
        + (wf?.completion_stimulation?.downhole_tubulars ? 1 : 0);

    const geologyCount = (wf?.geology?.formation_tops?.length ?? 0)
        + (wf?.geology?.hydrocarbon_shows?.length ?? 0);

    const casingCount = (wf?.casing_cement?.casing_program?.length ?? 0)
        + (wf?.casing_cement?.cementing_operations?.length ?? 0)
        + (wf?.casing_cement?.multi_stage_tools?.length ?? 0)
        + (wf?.casing_cement?.cement_evaluation ? 1 : 0);

    const drillingCount = (wf?.drilling?.drilling_fluid_params?.length ?? 0)
        + (wf?.drilling?.bit_runs?.length ?? 0)
        + (wf?.drilling?.wellbore_events?.length ?? 0);

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
                                <ParamCard label="True Vertical Depth (TVD)" value={fmtFeet(specs.tvd_ft)} />
                                <ParamCard label="Total Measured Depth (MD)" value={fmtFeet(specs.md_ft)} />
                                <ParamCard label="Lateral Length" value={fmtFeet(specs.lateral_length_ft)} />
                                <ParamCard label="Total Clean Fluid" value={fmtBarrels(specs.total_clean_fluid_bbls)} />
                                <ParamCard label="Total Proppant" value={fmtPounds(specs.total_proppant_lbs)} />
                                <ParamCard label="Max Treating Pressure" value={fmtPsi(specs.max_treating_pressure_psi)} />
                                {specs.casing_intermediate_depth_ft !== undefined && specs.casing_intermediate_depth_ft !== null && (
                                    <ParamCard label="Casing Intermediate Depth" value={fmtFeet(specs.casing_intermediate_depth_ft)} />
                                )}
                            </div>

                            {/* Completion Intensity KPIs */}
                            <h4 className="text-lg font-semibold text-gray-700 mb-4">
                                Completion Intensity
                            </h4>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-8">
                                <KpiCard
                                    label="Proppant Intensity"
                                    value={fmtIntensity(analysis.proppant_intensity_lbs_per_ft, 'lbs/ft')}
                                    colorScheme="purple"
                                />
                                <KpiCard
                                    label="Fluid Intensity"
                                    value={fmtIntensity(analysis.fluid_intensity_bbls_per_ft, 'bbls/ft')}
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
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg border border-gray-200 mb-8">
                                <div>
                                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Months on Production</p>
                                    <p className="text-lg font-mono font-bold text-gray-800">{prod.total_months}</p>
                                </div>
                                <div>
                                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Peak Oil (monthly)</p>
                                    <p className="text-lg font-mono font-bold text-gray-800">{fmtBarrels(prod.peak_oil_bbls)}</p>
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

                    {/* ── New collapsible sections ── */}
                    {wf && (
                        <div className="space-y-2">
                            <h4 className="text-lg font-semibold text-gray-700 mb-2">
                                Full Wellfile Data
                            </h4>

                            <CollapsibleSection
                                title="Completion & Stimulation"
                                count={completionCount}
                                accentClass="bg-orange-50 text-orange-800 hover:bg-orange-100"
                                defaultOpen={completionCount > 0}
                            >
                                {renderCompletion1(wf.completion_stimulation)}
                            </CollapsibleSection>

                            <CollapsibleSection
                                title="Geology"
                                count={geologyCount}
                                accentClass="bg-green-50 text-green-800 hover:bg-green-100"
                            >
                                {renderGeology(wf.geology)}
                            </CollapsibleSection>

                            <CollapsibleSection
                                title="Casing & Cement"
                                count={casingCount}
                                accentClass="bg-blue-50 text-blue-800 hover:bg-blue-100"
                            >
                                {renderCasingCement(wf.casing_cement)}
                            </CollapsibleSection>

                            <CollapsibleSection
                                title="Drilling"
                                count={drillingCount}
                                accentClass="bg-gray-100 text-gray-700 hover:bg-gray-200"
                            >
                                {renderDrilling(wf.drilling)}
                            </CollapsibleSection>
                        </div>
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
