import { useEffect, useState } from 'react';
import { getWells, getWellProduction, fitDecline, runEconomics, getFilterOptions } from './api/client';
import type { Well, ProductionRecord, DeclineResponse, EconomicMetrics, FilterOptions, FilterParams } from './api/client';
import { MapComponent } from './MapComponent';
import { Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ComposedChart, Area } from 'recharts';
import { Terminal, Activity, DollarSign, Filter } from 'lucide-react';

export function Dashboard() {
    const [wells, setWells] = useState<Well[]>([]);
    const [selectedWell, setSelectedWell] = useState<Well | null>(null);
    const [production, setProduction] = useState<ProductionRecord[]>([]);
    const [prediction, setPrediction] = useState<DeclineResponse | null>(null);
    const [economics, setEconomics] = useState<EconomicMetrics | null>(null);
    const [econParams, setEconParams] = useState({
        oilPrice: 70,
        capex: 6, // $MM
        discount: 10, // %
        opex: 10, // $/bbl
        abandonment: 5 // bbl/day
    });
    const [, setLoading] = useState(false);

    // Filter State
    const [filterOptions, setFilterOptions] = useState<FilterOptions | null>(null);
    const [filters, setFilters] = useState<FilterParams>({
        hasProduction: true,
        limit: 500
    });
    const [showFilters, setShowFilters] = useState(true);

    // Load Filter Options & Initial Wells
    useEffect(() => {
        getFilterOptions().then(setFilterOptions).catch(console.error);
    }, []);

    // Load Wells when filters change
    useEffect(() => {
        getWells(filters).then(setWells).catch(console.error);
    }, [filters]);

    const handleRunEconomics = async () => {
        if (!selectedWell) return;
        try {
            // Convert UI units to API units if needed
            const metrics = await runEconomics(
                selectedWell.API_WellNo,
                econParams.oilPrice,
                econParams.capex * 1_000_000, // Convert MM to raw
                econParams.opex,
                econParams.discount / 100, // Convert % to decimal
                econParams.abandonment
            );
            setEconomics(metrics);
        } catch (e) {
            console.error("Econ Failed", e);
        }
    };

    // When a well is selected, load its data
    useEffect(() => {
        if (!selectedWell) return;

        setLoading(true);
        setPrediction(null);
        setEconomics(null);

        // Load Production
        getWellProduction(selectedWell.API_WellNo)
            .then(data => {
                setProduction(data);
                if (data.length > 12) {
                    fitDecline(selectedWell.API_WellNo).then(setPrediction).catch(e => console.error("DCA Failed", e));
                    // Initial run with defaults
                    runEconomics(
                        selectedWell.API_WellNo,
                        econParams.oilPrice,
                        econParams.capex * 1_000_000,
                        econParams.opex,
                        econParams.discount / 100,
                        econParams.abandonment
                    ).then(setEconomics).catch(e => console.error("Econ Failed", e));
                }
            })
            .catch(console.error)
            .finally(() => setLoading(false));

    }, [selectedWell]);

    // Combine Historical and Forecast for Chart
    // We extend ProductionRecord with an optional Forecast_Oil & dateVal property
    type ChartPoint = Partial<ProductionRecord> & { Forecast_Oil?: number; dateVal: number };

    // Format historical data with numeric date
    const chartData: ChartPoint[] = production.map(p => ({
        ...p,
        dateVal: new Date(p.Rpt_Date).getTime()
    }));

    if (prediction) {
        // Append forecast
        // We need dates for forecast. Assuming monthly steps from last historical date?
        const lastDate = production.length > 0 ? new Date(production[production.length - 1].Rpt_Date) : new Date();

        prediction.forecast.production.forEach((val, idx) => {
            const d = new Date(lastDate);
            d.setMonth(d.getMonth() + idx + 1);
            // Add forecast point
            chartData.push({
                Rpt_Date: d.toISOString().split('T')[0],
                dateVal: d.getTime(), // Numeric timestamp
                Forecast_Oil: val
            });
        });
    }

    return (
        <div className="flex h-screen bg-gray-100 flex-col">
            <header className="bg-slate-800 text-white p-4 shadow-md flex items-center justify-between">
                <h1 className="text-xl font-bold flex items-center gap-2">
                    <Terminal className="w-6 h-6" /> MT Oil Analytics
                </h1>
                <div className="text-sm text-gray-400">
                    {wells.length} wells loaded
                </div>
            </header>

            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar / Map Area */}
                <div className="w-1/3 p-4 flex flex-col gap-4 overflow-y-auto">

                    {/* Filters Card */}
                    <div className="bg-white rounded-lg shadow-md p-4">
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
                            <div className="grid grid-cols-1 gap-3 text-sm animate-in fade-in slide-in-from-top-2 duration-300">
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

                    <div className="bg-white rounded-lg shadow-md h-[400px] overflow-hidden relative flex-shrink-0">
                        <MapComponent wells={wells} selectedWell={selectedWell} onSelectWell={setSelectedWell} />
                    </div>

                    {/* Economic Card */}
                    {economics && (
                        <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-green-500">
                            <h3 className="font-bold text-xl mb-4 flex items-center gap-2 text-gray-800">
                                <DollarSign className="w-6 h-6 text-green-600" /> Economics Analysis
                            </h3>

                            <div className="grid grid-cols-2 gap-6 mb-4">
                                <div>
                                    <p className="text-gray-500 text-xs uppercase tracking-wider font-semibold">NPV (10%)</p>
                                    <p className={`text-2xl font-mono font-bold ${economics.NPV >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                        ${economics.NPV.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-gray-500 text-xs uppercase tracking-wider font-semibold">ROI</p>
                                    <p className="text-2xl font-mono font-bold text-gray-800">{economics.ROI.toFixed(2)}x</p>
                                </div>
                                <div>
                                    <p className="text-gray-500 text-xs uppercase tracking-wider font-semibold">Payout</p>
                                    <p className="text-xl font-mono text-gray-800">{economics.Payout_Months > 0 ? `${economics.Payout_Months} mo` : 'N/A'}</p>
                                </div>
                                <div>
                                    <p className="text-gray-500 text-xs uppercase tracking-wider font-semibold">EUR</p>
                                    <p className="text-xl font-mono text-gray-800">{(economics.EUR / 1000).toFixed(1)}k bbl</p>
                                </div>
                            </div>

                            <div className="border-t pt-4">
                                <h4 className="text-sm font-semibold text-gray-700 mb-3 flex justify-between items-center">
                                    Assumptions
                                    <button
                                        onClick={handleRunEconomics}
                                        className="text-white bg-green-600 hover:bg-green-700 px-3 py-1 rounded text-xs transition-colors"
                                    >
                                        Recalculate
                                    </button>
                                </h4>
                                <div className="grid grid-cols-2 gap-3 text-sm">
                                    <div className="flex flex-col">
                                        <label className="text-xs text-gray-500 mb-1">Price ($/bbl)</label>
                                        <input
                                            type="number"
                                            value={econParams.oilPrice}
                                            onChange={(e) => setEconParams({ ...econParams, oilPrice: parseFloat(e.target.value) || 0 })}
                                            className="border rounded px-2 py-1 text-gray-700 focus:ring-2 focus:ring-green-500 outline-none"
                                        />
                                    </div>
                                    <div className="flex flex-col">
                                        <label className="text-xs text-gray-500 mb-1">CAPEX ($MM)</label>
                                        <input
                                            type="number"
                                            value={econParams.capex}
                                            onChange={(e) => setEconParams({ ...econParams, capex: parseFloat(e.target.value) || 0 })}
                                            className="border rounded px-2 py-1 text-gray-700 focus:ring-2 focus:ring-green-500 outline-none"
                                        />
                                    </div>
                                    <div className="flex flex-col">
                                        <label className="text-xs text-gray-500 mb-1">Discount (%)</label>
                                        <input
                                            type="number"
                                            value={econParams.discount}
                                            onChange={(e) => setEconParams({ ...econParams, discount: parseFloat(e.target.value) || 0 })}
                                            className="border rounded px-2 py-1 text-gray-700 focus:ring-2 focus:ring-green-500 outline-none"
                                        />
                                    </div>
                                    <div className="flex flex-col">
                                        <label className="text-xs text-gray-500 mb-1">OPEX ($/bbl)</label>
                                        <input
                                            type="number"
                                            value={econParams.opex}
                                            onChange={(e) => setEconParams({ ...econParams, opex: parseFloat(e.target.value) || 0 })}
                                            className="border rounded px-2 py-1 text-gray-700 focus:ring-2 focus:ring-green-500 outline-none"
                                        />
                                    </div>
                                    <div className="flex flex-col col-span-2">
                                        <label className="text-xs text-gray-500 mb-1">Abandonment (bbl/day)</label>
                                        <input
                                            type="number"
                                            value={econParams.abandonment}
                                            onChange={(e) => setEconParams({ ...econParams, abandonment: parseFloat(e.target.value) || 0 })}
                                            className="border rounded px-2 py-1 text-gray-700 focus:ring-2 focus:ring-green-500 outline-none"
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Main Content / Charts */}
                <div className="w-2/3 p-6 overflow-y-auto">
                    {selectedWell ? (
                        <div className="flex flex-col gap-6">
                            {/* Header */}
                            <div className="bg-white p-6 rounded-lg shadow-md">
                                <div className="flex justify-between items-start">
                                    <div>
                                        <h2 className="text-3xl font-bold text-gray-900">API: {selectedWell.API_WellNo}</h2>
                                        <p className="text-gray-500 mt-1">Location: {selectedWell.Lat.toFixed(4)}, {selectedWell.Long.toFixed(4)}</p>
                                    </div>
                                    {prediction && (
                                        <span className="bg-blue-100 text-blue-800 text-xs font-semibold px-3 py-1 rounded-full uppercase tracking-wide">
                                            DCA Method: {prediction.fit.method}
                                        </span>
                                    )}
                                </div>
                            </div>

                            {/* Chart */}
                            <div className="bg-white p-6 rounded-lg shadow-md h-[500px]">
                                <div className="flex justify-between items-center mb-6">
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
                                    <ResponsiveContainer width="100%" height="100%">
                                        <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
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
                                ) : (
                                    <div className="h-full flex flex-col items-center justify-center text-gray-400 border-2 border-dashed rounded-lg bg-gray-50">
                                        <Activity className="w-12 h-12 mb-2 opacity-20" />
                                        <p>No production history available for this well.</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div className="h-full flex items-center justify-center text-gray-400">
                            <p>Select a well from the map to view analysis</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
