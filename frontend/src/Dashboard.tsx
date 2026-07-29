import { useEffect, useState } from 'react';
import { getWells, getWellProduction, fitDecline, runEconomics, getFilterOptions } from './api/client';
import type { Well, ProductionRecord, DeclineResponse, EconomicMetrics, FilterOptions, FilterParams } from './api/client';
import { MapComponent } from './MapComponent';
import { Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ComposedChart, Area } from 'recharts';
import { Terminal, Activity, DollarSign, Filter, Loader2, Map, TrendingDown } from 'lucide-react';
import { toast } from 'sonner';

type TabType = 'map' | 'decline' | 'economics';

export function Dashboard() {
    const [wells, setWells] = useState<Well[]>([]);
    const [selectedWell, setSelectedWell] = useState<Well | null>(null);
    const [production, setProduction] = useState<ProductionRecord[]>([]);
    const [prediction, setPrediction] = useState<DeclineResponse | null>(null);
    const [economics, setEconomics] = useState<EconomicMetrics | null>(null);
    const [econParams, setEconParams] = useState({
        oilPrice: 70,
        gasPrice: 3.5,
        capex: 6, // $MM
        discount: 10, // %
        opex: 10, // $/bbl
        abandonment: 5 // bbl/day
    });
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState<TabType>('map');

    // Filter State
    const [filterOptions, setFilterOptions] = useState<FilterOptions | null>(null);
    const [filters, setFilters] = useState<FilterParams>({
        hasProduction: true,
        limit: 0
    });
    const [showFilters, setShowFilters] = useState(true);

    // Load Filter Options & Initial Wells
    useEffect(() => {
        const loadInitial = async () => {
            try {
                const opts = await getFilterOptions();
                setFilterOptions(opts);
            } catch (e) {
                console.error(e);
                toast.error("Failed to load filter options");
            }
        };
        loadInitial();
    }, []);

    // Load Wells when filters change
    useEffect(() => {
        const loadWells = async () => {
            try {
                const data = await getWells(filters);
                setWells(data);
            } catch (e) {
                console.error(e);
                toast.error("Failed to load wells");
            }
        };
        loadWells();
    }, [filters]);

    const handleRunEconomics = async () => {
        if (!selectedWell) return;
        try {
            const metrics = await runEconomics(
                selectedWell.API_WellNo,
                econParams.oilPrice,
                econParams.capex * 1_000_000,
                econParams.opex,
                econParams.discount / 100,
                econParams.abandonment,
                econParams.gasPrice
            );
            setEconomics(metrics);
            toast.success("Economics recalculated");
        } catch (e) {
            console.error("Econ Failed", e);
            toast.error("Failed to calculate economics");
        }
    };

    // When a well is selected, load its data
    useEffect(() => {
        if (!selectedWell) return;

        setLoading(true);
        setPrediction(null);
        setEconomics(null);

        const fetchData = async () => {
            try {
                const data = await getWellProduction(selectedWell.API_WellNo);
                setProduction(data);

                if (data.length > 12) {
                    try {
                        const pred = await fitDecline(selectedWell.API_WellNo);
                        setPrediction(pred);
                    } catch (e) {
                        console.error("DCA Failed", e);
                        toast.error("Failed to forecast decline curve");
                    }

                    try {
                        const econ = await runEconomics(
                            selectedWell.API_WellNo,
                            econParams.oilPrice,
                            econParams.capex * 1_000_000,
                            econParams.opex,
                            econParams.discount / 100,
                            econParams.abandonment,
                            econParams.gasPrice
                        );
                        setEconomics(econ);
                    } catch (e) {
                        console.error("Econ Failed", e);
                        toast.error("Failed to run initial economics");
                    }
                } else if (data.length === 0) {
                    toast.info("No production history for this well");
                }
            } catch (e) {
                console.error(e);
                toast.error("Failed to load production data");
            } finally {
                setLoading(false);
            }
        };

        fetchData();

    }, [selectedWell]);

    // Combine Historical and Forecast for Chart
    type ChartPoint = Partial<ProductionRecord> & { Forecast_Oil?: number; dateVal: number };

    const chartData: ChartPoint[] = production.map(p => ({
        ...p,
        dateVal: new Date(p.Rpt_Date).getTime()
    }));

    if (prediction) {
        const lastDate = production.length > 0 ? new Date(production[production.length - 1].Rpt_Date) : new Date();

        prediction.forecast.production.forEach((val, idx) => {
            const d = new Date(lastDate);
            d.setMonth(d.getMonth() + idx + 1);
            chartData.push({
                Rpt_Date: d.toISOString().split('T')[0],
                dateVal: d.getTime(),
                Forecast_Oil: val
            });
        });
    }

    const tabs = [
        { id: 'map' as TabType, label: 'Map', icon: Map },
        { id: 'decline' as TabType, label: 'Decline Curve', icon: TrendingDown },
        { id: 'economics' as TabType, label: 'Economics', icon: DollarSign },
    ];

    return (
        <div className="flex h-screen bg-gray-100 flex-col">
            <header className="bg-slate-800 text-white p-4 shadow-md flex items-center justify-between">
                <h1 className="text-lg sm:text-xl font-bold flex items-center gap-2">
                    <Terminal className="w-6 h-6" /> MT Oil Analytics
                </h1>
                <div className="text-sm text-gray-400">
                    {wells.length} wells loaded
                </div>
            </header>

            {/* Tab Navigation */}
            <div className="bg-white border-b border-gray-200 px-3 sm:px-6">
                <div className="flex gap-1">
                    {tabs.map(tab => {
                        const Icon = tab.icon;
                        return (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`flex items-center gap-2 px-3 sm:px-6 py-2 sm:py-3 font-medium transition-colors border-b-2 ${activeTab === tab.id
                                    ? 'border-blue-600 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }`}
                            >
                                <Icon className="w-4 h-4" />
                                {tab.label}
                            </button>
                        );
                    })}
                </div>
            </div>

            <div className="flex flex-1 overflow-hidden">
                {/* Map Tab */}
                {activeTab === 'map' && (
                    <div className="flex flex-1 overflow-hidden relative">
                        {loading && (
                            <div className="absolute inset-0 bg-white/50 backdrop-blur-sm flex items-center justify-center z-50">
                                <div className="bg-white p-4 rounded-lg shadow-lg flex items-center gap-3">
                                    <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
                                    <span className="font-semibold text-gray-700">Analyzing Data...</span>
                                </div>
                            </div>
                        )}
                        {/* Sidebar with Filters */}
                        <div className="w-72 lg:w-80 p-4 flex flex-col gap-4 overflow-y-auto border-r border-gray-200 bg-white">
                            {/* Filters Card */}
                            <div className="bg-gray-50 rounded-lg shadow-sm p-4 border border-gray-200">
                                <div
                                    className="flex justify-between items-center cursor-pointer mb-2"
                                    onClick={() => setShowFilters(!showFilters)}
                                >
                                    <h3 className="font-bold text-gray-700 flex items-center gap-2">
                                        <Filter className="w-4 h-4" /> Filter Wells
                                    </h3>
                                    <span className="text-xs text-gray-400">{showFilters ? 'Hide' : 'Show'}</span>
                                </div>

                                {showFilters && filterOptions && (
                                    <div className="grid grid-cols-1 gap-3 text-sm">
                                        <div>
                                            <label className="block text-xs font-semibold text-gray-500 mb-1">Well Type</label>
                                            <select
                                                className="w-full border rounded px-2 py-1 text-gray-700 bg-white"
                                                value={filters.wellType || ''}
                                                onChange={(e) => setFilters({ ...filters, wellType: e.target.value || undefined })}
                                            >
                                                <option value="">All Types</option>
                                                {filterOptions.well_types.map(t => <option key={t} value={t}>{t}</option>)}
                                            </select>
                                        </div>
                                        <div>
                                            <label className="block text-xs font-semibold text-gray-500 mb-1">Formation</label>
                                            <select
                                                className="w-full border rounded px-2 py-1 text-gray-700 bg-white"
                                                value={filters.formation || ''}
                                                onChange={(e) => setFilters({ ...filters, formation: e.target.value || undefined })}
                                            >
                                                <option value="">All Formations</option>
                                                {filterOptions.formations.map(f => <option key={f} value={f}>{f}</option>)}
                                            </select>
                                        </div>
                                        <div>
                                            <label className="block text-xs font-semibold text-gray-500 mb-1">Trajectory</label>
                                            <select
                                                className="w-full border rounded px-2 py-1 text-gray-700 bg-white"
                                                value={filters.slant || ''}
                                                onChange={(e) => setFilters({ ...filters, slant: e.target.value || undefined })}
                                            >
                                                <option value="">All Trajectories</option>
                                                {filterOptions.slants.map(s => <option key={s} value={s}>{s}</option>)}
                                            </select>
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Selected Well Info */}
                            {selectedWell && (
                                <div className="bg-blue-50 rounded-lg shadow-sm p-4 border border-blue-200">
                                    <h3 className="font-bold text-sm text-blue-900 mb-2">Selected Well</h3>
                                    <p className="text-xs text-blue-700 font-mono">{selectedWell.API_WellNo}</p>
                                    <p className="text-xs text-blue-600 mt-1">
                                        {selectedWell.Lat.toFixed(4)}, {selectedWell.Long.toFixed(4)}
                                    </p>
                                </div>
                            )}
                        </div>

                        {/* Map */}
                        <div className="flex-1">
                            <div className="bg-white h-full overflow-hidden">
                                <MapComponent wells={wells} selectedWell={selectedWell} onSelectWell={setSelectedWell} />
                            </div>
                        </div>
                    </div>
                )}

                {/* Decline Curve Tab */}
                {activeTab === 'decline' && (
                    <div className="flex-1 overflow-y-auto flex flex-col">
                        {selectedWell ? (
                            <>
                                {/* Header */}
                                <div className="bg-white shadow-md flex-shrink-0">
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <h2 className="text-2xl font-bold text-gray-900">API: {selectedWell.API_WellNo}</h2>
                                            <p className="text-gray-500 mt-1">Location: {selectedWell.Lat.toFixed(4)}, {selectedWell.Long.toFixed(4)}</p>
                                        </div>
                                        {prediction && (
                                            <span className="bg-blue-100 text-blue-800 text-xs font-semibold px-3 py-1 rounded-full uppercase tracking-wide">
                                                DCA Method: {prediction.fit.method}
                                            </span>
                                        )}
                                    </div>
                                </div>

                                {/* Chart - Flex to fill remaining space */}
                                <div className="flex-1 bg-white shadow-md flex flex-col">
                                    <div className="flex justify-between items-center px-2 py-1 flex-shrink-0">
                                        <h3 className="font-semibold text-lg text-gray-700 flex items-center gap-2">
                                            <Activity className="w-5 h-5" /> Production Profile
                                        </h3>
                                        <div className="flex gap-4 text-xs font-medium">
                                            <div className="flex items-center gap-1">
                                                <div className="w-3 h-3 bg-blue-500 rounded-sm"></div> Historical
                                            </div>
                                            <div className="flex items-center gap-1">
                                                <div className="w-3 h-3 border-b-2 border-orange-500 border-dashed"></div> Forecast
                                            </div>
                                        </div>
                                    </div>

                                    {production.length > 0 ? (
                                        <div className="flex-1 w-full">
                                            <ResponsiveContainer width="100%" height="100%">
                                                <ComposedChart data={chartData} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                                                    <CartesianGrid strokeDasharray="3 3" opacity={0.1} vertical={false} />
                                                    <XAxis
                                                        dataKey="dateVal"
                                                        type="number"
                                                        scale="time"
                                                        domain={['dataMin', 'dataMax']}
                                                        tickFormatter={(v) => new Date(v).getFullYear().toString()}
                                                        minTickGap={30}
                                                        tick={{ fontSize: 12 }}
                                                    />
                                                    <YAxis
                                                        tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                                                        label={{ value: 'Oil (bbl/month)', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle' } }}
                                                    />
                                                    <Tooltip
                                                        labelFormatter={(value) => `Date: ${new Date(value).toLocaleDateString(undefined, { year: 'numeric', month: 'short' })}`}
                                                        formatter={(value: number) => [value.toFixed(0), 'Barrels']}
                                                        contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                                                    />
                                                    <Legend />
                                                    <Area
                                                        type="monotone"
                                                        dataKey="BBLS_OIL_COND"
                                                        name="Historical Oil"
                                                        stroke="#3b82f6"
                                                        fill="#3b82f6"
                                                        fillOpacity={0.2}
                                                        strokeWidth={2}
                                                    />
                                                    <Line
                                                        type="monotone"
                                                        dataKey="Forecast_Oil"
                                                        name="DCA Forecast"
                                                        stroke="#f97316"
                                                        strokeDasharray="5 5"
                                                        strokeWidth={3}
                                                        dot={false}
                                                        connectNulls={true}
                                                    />
                                                </ComposedChart>
                                            </ResponsiveContainer>
                                        </div>
                                    ) : (
                                        <div className="flex-1 flex flex-col items-center justify-center text-gray-400 border-2 border-dashed rounded-lg bg-gray-50">
                                            <Activity className="w-12 h-12 mb-2 opacity-20" />
                                            <p>No production history available for this well.</p>
                                        </div>
                                    )}
                                </div>
                            </>
                        ) : (
                            <div className="h-full flex items-center justify-center text-gray-400">
                                <div className="text-center">
                                    <TrendingDown className="w-16 h-16 mx-auto mb-4 opacity-20" />
                                    <p className="text-lg">Select a well from the Map tab to view decline curve analysis</p>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* Economics Tab */}
                {activeTab === 'economics' && (
                    <div className="flex-1 overflow-y-auto">
                        {selectedWell && economics ? (
                            <div className="w-full">
                                <div className="bg-white p-8 rounded-lg shadow-md border-l-4 border-green-500">
                                    <h3 className="font-bold text-2xl mb-6 flex items-center gap-2 text-gray-800">
                                        <DollarSign className="w-8 h-8 text-green-600" /> Economics Analysis
                                    </h3>

                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-8 mb-8">
                                        <div className="bg-gradient-to-br from-green-50 to-green-100 p-6 rounded-lg">
                                            <p className="text-gray-600 text-sm uppercase tracking-wider font-semibold mb-2">NPV (10%)</p>
                                            <p className={`text-4xl font-mono font-bold ${economics.NPV >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                                                ${economics.NPV.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                                            </p>
                                        </div>
                                        <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-6 rounded-lg">
                                            <p className="text-gray-600 text-sm uppercase tracking-wider font-semibold mb-2">ROI</p>
                                            <p className="text-4xl font-mono font-bold text-blue-700">{economics.ROI.toFixed(2)}x</p>
                                        </div>
                                        <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-6 rounded-lg">
                                            <p className="text-gray-600 text-sm uppercase tracking-wider font-semibold mb-2">Payout Period</p>
                                            <p className="text-3xl font-mono text-purple-700">{economics.Payout_Months > 0 ? `${economics.Payout_Months} months` : 'N/A'}</p>
                                        </div>
                                        <div className="bg-gradient-to-br from-orange-50 to-orange-100 p-6 rounded-lg">
                                            <p className="text-gray-600 text-sm uppercase tracking-wider font-semibold mb-2">EUR</p>
                                            <p className="text-3xl font-mono text-orange-700">{(economics.EUR / 1000).toFixed(1)}k bbl</p>
                                        </div>
                                    </div>

                                    <div className="border-t pt-6">
                                        <h4 className="text-lg font-semibold text-gray-700 mb-4 flex justify-between items-center">
                                            Economic Assumptions
                                            <button
                                                onClick={handleRunEconomics}
                                                className="text-white bg-green-600 hover:bg-green-700 px-4 py-2 rounded text-sm transition-colors shadow-sm"
                                            >
                                                Recalculate
                                            </button>
                                        </h4>
                                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                                            <div className="flex flex-col">
                                                <label className="text-sm text-gray-600 mb-2 font-medium">Oil Price ($/bbl)</label>
                                                <input
                                                    type="number"
                                                    value={econParams.oilPrice}
                                                    onChange={(e) => setEconParams({ ...econParams, oilPrice: parseFloat(e.target.value) || 0 })}
                                                    className="border border-gray-300 rounded px-3 py-2 text-gray-700 focus:ring-2 focus:ring-green-500 outline-none"
                                                />
                                            </div>
                                            <div className="flex flex-col">
                                                <label className="text-sm text-gray-600 mb-2 font-medium">CAPEX ($MM)</label>
                                                <input
                                                    type="number"
                                                    value={econParams.capex}
                                                    onChange={(e) => setEconParams({ ...econParams, capex: parseFloat(e.target.value) || 0 })}
                                                    className="border border-gray-300 rounded px-3 py-2 text-gray-700 focus:ring-2 focus:ring-green-500 outline-none"
                                                />
                                            </div>
                                            <div className="flex flex-col">
                                                <label className="text-sm text-gray-600 mb-2 font-medium">Discount Rate (%)</label>
                                                <input
                                                    type="number"
                                                    value={econParams.discount}
                                                    onChange={(e) => setEconParams({ ...econParams, discount: parseFloat(e.target.value) || 0 })}
                                                    className="border border-gray-300 rounded px-3 py-2 text-gray-700 focus:ring-2 focus:ring-green-500 outline-none"
                                                />
                                            </div>
                                            <div className="flex flex-col">
                                                <label className="text-sm text-gray-600 mb-2 font-medium">OPEX ($/bbl)</label>
                                                <input
                                                    type="number"
                                                    value={econParams.opex}
                                                    onChange={(e) => setEconParams({ ...econParams, opex: parseFloat(e.target.value) || 0 })}
                                                    className="border border-gray-300 rounded px-3 py-2 text-gray-700 focus:ring-2 focus:ring-green-500 outline-none"
                                                />
                                            </div>
                                            <div className="flex flex-col col-span-2">
                                                <label className="text-sm text-gray-600 mb-2 font-medium">Abandonment Rate (bbl/day)</label>
                                                <input
                                                    type="number"
                                                    value={econParams.abandonment}
                                                    onChange={(e) => setEconParams({ ...econParams, abandonment: parseFloat(e.target.value) || 0 })}
                                                    className="border border-gray-300 rounded px-3 py-2 text-gray-700 focus:ring-2 focus:ring-green-500 outline-none"
                                                />
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="h-full flex items-center justify-center text-gray-400">
                                <div className="text-center">
                                    <DollarSign className="w-16 h-16 mx-auto mb-4 opacity-20" />
                                    <p className="text-lg">Select a well from the Map tab to view economics analysis</p>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
