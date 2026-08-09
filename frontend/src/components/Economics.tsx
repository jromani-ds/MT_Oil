import type { EconomicMetrics, Well, WellfileResponse } from '../api/client';
import { DollarSign, Loader2 } from 'lucide-react';
import { KpiCard } from './KpiCard';
import { formatCurrency, formatMultiplier, formatDuration, formatVolume } from '../utils/format';

interface EconParams {
  oilPrice: number;
  gasPrice: number;
  capex: number;
  discount: number;
  opex: number;
  abandonment: number;
}

interface EconomicsProps {
  selectedWell: Well | null;
  loading: boolean;
  economics: EconomicMetrics | null;
  econParams: EconParams;
  wellfileUrl: WellfileResponse | null;
  onParamChange: (params: EconParams) => void;
  onRecalculate: () => void;
}

export function Economics({
  selectedWell,
  loading,
  economics,
  econParams,
  wellfileUrl,
  onParamChange,
  onRecalculate,
}: EconomicsProps) {
  if (!selectedWell) {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="h-full flex items-center justify-center text-gray-400">
          <div className="text-center">
            <DollarSign className="w-16 h-16 mx-auto mb-4 opacity-20" />
            <p className="text-lg">Select a well from the Map tab to view economics analysis</p>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="h-full flex items-center justify-center text-gray-400">
          <div className="text-center">
            <Loader2 className="w-16 h-16 mx-auto mb-4 opacity-20 animate-spin" />
            <p className="text-lg">Loading economics data...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!economics) {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="h-full flex items-center justify-center text-gray-400">
          <div className="text-center">
            <DollarSign className="w-16 h-16 mx-auto mb-4 opacity-20" />
            <p className="text-lg">No economic data available for this well.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="w-full p-4 sm:p-6 lg:p-8">
        <div className="bg-white rounded-lg shadow-md border-l-4 border-green-500 p-4 sm:p-6 lg:p-8">
          {/* Header */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
            <h3 className="font-bold text-2xl flex items-center gap-2 text-gray-800">
              <DollarSign className="w-8 h-8 text-green-600" /> Economics Analysis
            </h3>
            <div className="flex items-center gap-3 bg-gray-50 rounded-lg p-2">
              {wellfileUrl && (
                <a
                  href={wellfileUrl.primary_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-white bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded text-sm transition-colors shadow-sm flex items-center gap-2 min-w-[140px] justify-center"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Download Official Wellfile
                </a>
              )}
              <button
                onClick={onRecalculate}
                className="text-white bg-green-600 hover:bg-green-700 px-4 py-2 rounded text-sm transition-colors shadow-sm min-w-[140px] justify-center flex items-center gap-2"
              >
                Recalculate
              </button>
            </div>
          </div>

          {/* KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <KpiCard
              label="NPV (10%)"
              value={formatCurrency(economics.NPV)}
              colorScheme="green"
              negative={economics.NPV < 0}
            />
            <KpiCard
              label="ROI"
              value={formatMultiplier(economics.ROI)}
              colorScheme="blue"
            />
            <KpiCard
              label="Payout Period"
              value={formatDuration(economics.Payout_Months)}
              colorScheme="purple"
            />
            <KpiCard
              label="EUR"
              value={formatVolume(economics.EUR)}
              colorScheme="orange"
            />
          </div>

          {/* Economic Assumptions */}
          <div className="border-t pt-6">
            <h4 className="text-lg font-semibold text-gray-700 mb-4">
              Economic Assumptions
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="flex flex-col">
                <label className="text-sm text-gray-600 mb-2 font-medium" htmlFor="oil-price">Oil Price ($/bbl)</label>
                <input
                  id="oil-price"
                  type="number"
                  min={0}
                  step={0.5}
                  value={econParams.oilPrice}
                  onChange={(e) => onParamChange({ ...econParams, oilPrice: parseFloat(e.target.value) || 0 })}
                  className="border border-gray-300 rounded px-3 py-2 text-gray-700 focus:ring-2 focus:ring-green-500 outline-none"
                />
              </div>
              <div className="flex flex-col">
                <label className="text-sm text-gray-600 mb-2 font-medium" htmlFor="capex">CAPEX ($MM)</label>
                <input
                  id="capex"
                  type="number"
                  min={0}
                  step={0.1}
                  value={econParams.capex}
                  onChange={(e) => onParamChange({ ...econParams, capex: parseFloat(e.target.value) || 0 })}
                  className="border border-gray-300 rounded px-3 py-2 text-gray-700 focus:ring-2 focus:ring-green-500 outline-none"
                />
              </div>
              <div className="flex flex-col">
                <label className="text-sm text-gray-600 mb-2 font-medium" htmlFor="discount-rate">Discount Rate (%)</label>
                <input
                  id="discount-rate"
                  type="number"
                  min={0}
                  max={100}
                  step={0.5}
                  value={econParams.discount}
                  onChange={(e) => onParamChange({ ...econParams, discount: parseFloat(e.target.value) || 0 })}
                  className="border border-gray-300 rounded px-3 py-2 text-gray-700 focus:ring-2 focus:ring-green-500 outline-none"
                />
              </div>
              <div className="flex flex-col">
                <label className="text-sm text-gray-600 mb-2 font-medium" htmlFor="opex">OPEX ($/bbl)</label>
                <input
                  id="opex"
                  type="number"
                  min={0}
                  step={0.5}
                  value={econParams.opex}
                  onChange={(e) => onParamChange({ ...econParams, opex: parseFloat(e.target.value) || 0 })}
                  className="border border-gray-300 rounded px-3 py-2 text-gray-700 focus:ring-2 focus:ring-green-500 outline-none"
                />
              </div>
              <div className="flex flex-col">
                <label className="text-sm text-gray-600 mb-2 font-medium" htmlFor="abandonment">Abandonment Rate (bbl/day)</label>
                <input
                  id="abandonment"
                  type="number"
                  min={0}
                  step={0.5}
                  value={econParams.abandonment}
                  onChange={(e) => onParamChange({ ...econParams, abandonment: parseFloat(e.target.value) || 0 })}
                  className="border border-gray-300 rounded px-3 py-2 text-gray-700 focus:ring-2 focus:ring-green-500 outline-none"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
