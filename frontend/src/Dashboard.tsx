import { useEffect, useState, useRef } from 'react';
import { getWells, getWellProduction, fitDecline, runEconomics, getWellfileUrl, getFilterOptions } from './api/client';
import type { Well, ProductionRecord, DeclineResponse, EconomicMetrics, FilterOptions, FilterParams, WellfileResponse } from './api/client';
import { MapComponent } from './MapComponent';
import { useGisFeatureCounts } from './GisLayers';
import type { GisLayerState } from './GisLayers';
import { Map, TrendingDown, DollarSign, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Header } from './components/Header';
import { MapSidebar } from './components/MapSidebar';
import { DeclineCurve } from './components/DeclineCurve';
import { Economics } from './components/Economics';

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
        capex: 6,
        discount: 10,
        opex: 10,
        abandonment: 5,
    });
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState<TabType>('map');
    const [wellfileUrl, setWellfileUrl] = useState<WellfileResponse | null>(null);
    const econParamsRef = useRef(econParams);
    useEffect(() => {
        econParamsRef.current = econParams;
    }, [econParams]);

    const [filterOptions, setFilterOptions] = useState<FilterOptions | null>(null);
    const [filters, setFilters] = useState<FilterParams>({
        hasProduction: true,
        limit: 0,
    });
    const [showFilters, setShowFilters] = useState(true);

    const [gisLayers, setGisLayers] = useState<GisLayerState>({
        paths: false,
        fields: false,
        units: false,
    });
    const gisFeatureCounts = useGisFeatureCounts(gisLayers);

    const toggleGisLayer = (key: keyof GisLayerState) => {
        setGisLayers(prev => ({ ...prev, [key]: !prev[key] }));
    };

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
                econParams.gasPrice,
            );
            setEconomics(metrics);
            toast.success("Economics recalculated");
        } catch (e) {
            console.error("Econ Failed", e);
            toast.error("Failed to calculate economics");
        }
    };

    const handleSelectWell = (well: Well) => {
        setSelectedWell(well);
        setLoading(true);
        setPrediction(null);
        setEconomics(null);
        setWellfileUrl(null);
        setProduction([]);
    };

    useEffect(() => {
        if (!selectedWell) return;

        const apiNumber = selectedWell.API_WellNo;

        Promise.all([
            getWellProduction(apiNumber),
            getWellfileUrl(apiNumber).catch(() => null),
        ])
            .then(([prod, wf]) => {
                setProduction(prod);
                setWellfileUrl(wf as WellfileResponse | null);

                if (prod.length > 12) {
                    fitDecline(apiNumber)
                        .then(setPrediction)
                        .catch(() => {
                            toast.error("Failed to forecast decline curve");
                        });
                    runEconomics(
                        apiNumber,
                        econParamsRef.current.oilPrice,
                        econParamsRef.current.capex * 1_000_000,
                        econParamsRef.current.opex,
                        econParamsRef.current.discount / 100,
                        econParamsRef.current.abandonment,
                        econParamsRef.current.gasPrice,
                    )
                        .then(setEconomics)
                        .catch(() => {
                            toast.error("Failed to run initial economics");
                        });
                } else if (prod.length === 0) {
                    toast.info("No production history for this well");
                }
            })
            .catch(() => {
                toast.error("Failed to load production data");
            })
            .finally(() => {
                setLoading(false);
            });
    }, [selectedWell]);

    const tabs = [
        { id: 'map' as TabType, label: 'Map', icon: Map },
        { id: 'decline' as TabType, label: 'Decline Curve', icon: TrendingDown },
        { id: 'economics' as TabType, label: 'Economics', icon: DollarSign },
    ];

    return (
        <div className="flex h-screen bg-gray-100 flex-col">
            <Header wellCount={wells.length} />

            {/* Tab Navigation */}
            <div className="bg-white border-b border-gray-200 px-3 sm:px-6">
                <div className="flex gap-1">
                    {tabs.map(tab => {
                        const Icon = tab.icon;
                        return (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                data-testid={`tab-${tab.id}`}
                                className={`flex items-center gap-2 px-3 sm:px-6 py-2 sm:py-3 font-medium transition-colors border-b-2 ${
                                    activeTab === tab.id
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

            <div className="flex flex-1 overflow-hidden relative">
                {loading && (
                    <div className="absolute inset-0 bg-white/50 backdrop-blur-sm flex items-center justify-center z-50">
                        <div className="bg-white p-4 rounded-lg shadow-lg flex items-center gap-3">
                            <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
                            <span className="font-semibold text-gray-700">Analyzing Data...</span>
                        </div>
                    </div>
                )}

                {activeTab === 'map' && (
                    <div className="flex flex-1 overflow-hidden">
                        <MapSidebar
                            filterOptions={filterOptions}
                            filters={filters}
                            showFilters={showFilters}
                            selectedWell={selectedWell}
                            gisLayers={gisLayers}
                            gisFeatureCounts={gisFeatureCounts}
                            onToggleFilters={() => setShowFilters(!showFilters)}
                            onFilterChange={setFilters}
                            onToggleGisLayer={toggleGisLayer}
                        />
                        <div className="flex-1">
                            <div className="bg-white h-full overflow-hidden">
                                <MapComponent
                                    wells={wells}
                                    selectedWell={selectedWell}
                                    onSelectWell={handleSelectWell}
                                    gisLayers={gisLayers}
                                />
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'decline' && (
                    <DeclineCurve
                        selectedWell={selectedWell}
                        loading={loading}
                        production={production}
                        prediction={prediction}
                    />
                )}

                {activeTab === 'economics' && (
                    <Economics
                        selectedWell={selectedWell}
                        loading={loading}
                        economics={economics}
                        econParams={econParams}
                        wellfileUrl={wellfileUrl}
                        onParamChange={setEconParams}
                        onRecalculate={handleRunEconomics}
                    />
                )}
            </div>
        </div>
    );
}
