import type { ProductionRecord, DeclineResponse, Well } from '../api/client';
import { Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ComposedChart, Area } from 'recharts';
import { Activity, TrendingDown, Loader2, Flame, Droplets } from 'lucide-react';
import { formatCoordinate, formatYear, formatChartDate } from '../utils/format';

type ChartPoint = Partial<ProductionRecord> & { Forecast_Oil?: number; Forecast_Gas?: number; dateVal: number };

function buildChartData(production: ProductionRecord[], prediction: DeclineResponse | null): ChartPoint[] {
  const data: ChartPoint[] = production.map(p => ({
    ...p,
    BBLS_OIL_COND: Math.max(0, p.BBLS_OIL_COND || 0),
    MCF_GAS: Math.max(0, p.MCF_GAS || 0),
    dateVal: new Date(p.Rpt_Date).getTime(),
  }));

  if (prediction) {
    const lastDate = production.length > 0
      ? new Date(production[production.length - 1].Rpt_Date)
      : new Date();
    const stream = prediction.stream || 'oil';

    prediction.forecast.production.forEach((val, idx) => {
      const d = new Date(lastDate);
      d.setMonth(d.getMonth() + idx + 1);
      const pt: ChartPoint = {
        Rpt_Date: d.toISOString().split('T')[0],
        dateVal: d.getTime(),
      };
      if (stream === 'oil') {
        pt.Forecast_Oil = Math.max(0, val);
      } else {
        pt.Forecast_Gas = Math.max(0, val);
      }
      data.push(pt);
    });
  }

  return data;
}

function getYearTicks(data: ChartPoint[]): number[] {
  const years = new Set<number>();
  for (const d of data) {
    const year = new Date(d.dateVal).getFullYear();
    years.add(year);
  }
  return Array.from(years).sort((a, b) => a - b).map(y => new Date(y, 6, 1).getTime())
    .filter(t => t >= data[0]?.dateVal && t <= data[data.length - 1]?.dateVal);
}

interface DeclineCurveProps {
  selectedWell: Well | null;
  loading: boolean;
  production: ProductionRecord[];
  prediction: DeclineResponse | null;
}

export function DeclineCurve({ selectedWell, loading, production, prediction }: DeclineCurveProps) {
  if (!selectedWell) {
    return (
      <div className="flex-1 overflow-y-auto flex flex-col">
        <div className="h-full flex items-center justify-center text-gray-400">
          <div className="text-center">
            <TrendingDown className="w-16 h-16 mx-auto mb-4 opacity-20" />
            <p className="text-lg">Select a well from the Map tab to view decline curve analysis</p>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex-1 overflow-y-auto flex flex-col">
        <div className="h-full flex items-center justify-center text-gray-400">
          <div className="text-center">
            <Loader2 className="w-16 h-16 mx-auto mb-4 opacity-20 animate-spin" />
            <p className="text-lg">Loading production data...</p>
          </div>
        </div>
      </div>
    );
  }

  const chartData = buildChartData(production, prediction);
  const yearTicks = getYearTicks(chartData);

  // Summary statistics
  const peakOil = production.reduce((m, r) => Math.max(m, r.BBLS_OIL_COND || 0), 0);
  const peakGas = production.reduce((m, r) => Math.max(m, r.MCF_GAS || 0), 0);
  const totalOil = production.reduce((s, r) => s + (r.BBLS_OIL_COND || 0), 0);
  const totalGas = production.reduce((s, r) => s + (r.MCF_GAS || 0), 0);
  const stream = prediction?.stream || 'oil';

  return (
    <div className="flex-1 overflow-y-auto flex flex-col">
      {/* Header */}
      <div className="bg-white shadow-md flex-shrink-0 px-4 sm:px-6 py-3">
        <div className="flex justify-between items-start">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">API: {selectedWell.API_WellNo}</h2>
            <p className="text-gray-500 mt-1">
              Location: {formatCoordinate(selectedWell.Lat)}, {formatCoordinate(selectedWell.Long)}
            </p>
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 px-4 pt-4">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center gap-2 text-blue-600 mb-1">
            <Activity className="w-4 h-4" />
            <span className="text-xs font-semibold uppercase tracking-wider">Peak Oil</span>
          </div>
          <p className="text-lg font-bold text-gray-900">{Math.round(peakOil).toLocaleString()} <span className="text-sm font-normal text-gray-500">bbl/mo</span></p>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center gap-2 text-green-600 mb-1">
            <Flame className="w-4 h-4" />
            <span className="text-xs font-semibold uppercase tracking-wider">Peak Gas</span>
          </div>
          <p className="text-lg font-bold text-gray-900">{Math.round(peakGas).toLocaleString()} <span className="text-sm font-normal text-gray-500">MCF/mo</span></p>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center gap-2 text-blue-600 mb-1">
            <Droplets className="w-4 h-4" />
            <span className="text-xs font-semibold uppercase tracking-wider">Total Oil</span>
          </div>
          <p className="text-lg font-bold text-gray-900">{Math.round(totalOil).toLocaleString()} <span className="text-sm font-normal text-gray-500">bbl</span></p>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center gap-2 text-green-600 mb-1">
            <Flame className="w-4 h-4" />
            <span className="text-xs font-semibold uppercase tracking-wider">Total Gas</span>
          </div>
          <p className="text-lg font-bold text-gray-900">{Math.round(totalGas).toLocaleString()} <span className="text-sm font-normal text-gray-500">MCF</span></p>
        </div>
      </div>

      {/* Chart */}
      <div className="flex-1 bg-white shadow-md flex flex-col m-4 rounded-lg overflow-hidden">
        <div className="flex justify-between items-center px-4 py-3 flex-shrink-0 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <h3 className="font-semibold text-lg text-gray-700 flex items-center gap-2">
              <Activity className="w-5 h-5" /> Production Profile
            </h3>
            {prediction && (
              <span className="bg-blue-100 text-blue-800 text-xs font-semibold px-3 py-1 rounded-full uppercase tracking-wide">
                {stream === 'gas' ? 'Gas DCA' : 'Oil DCA'}: {prediction.fit.method}
              </span>
            )}
          </div>
          <div className="flex flex-col gap-2 text-xl font-medium">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-600 rounded border border-blue-700 shadow-sm"></div>
              <span className="text-gray-700">Oil</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-600 rounded border border-green-700 shadow-sm"></div>
              <span className="text-gray-700">Gas</span>
            </div>
            <div className="flex items-center gap-3">
              <svg className="w-16 h-10" viewBox="0 0 128 80">
                <line x1="0" y1="40" x2="128" y2="40" stroke="#f97316" strokeWidth="16" strokeDasharray="24 12" />
              </svg>
              <span className="text-gray-700">Forecast</span>
            </div>
          </div>
        </div>

        {production.length > 0 ? (
           <div className="flex-1 w-full p-2">
             <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.1} vertical={false} />
                <XAxis
                  dataKey="dateVal"
                  type="number"
                  scale="time"
                  domain={['dataMin', 'dataMax']}
                  ticks={yearTicks}
                  tickFormatter={formatYear}
                  tick={{ fontSize: 12 }}
                />
                <YAxis
                  yAxisId="oil"
                  domain={[0, 'auto']}
                  tickFormatter={(v) => {
                    if (v === 0) return '0k';
                    const val = v / 1000;
                    return val % 1 === 0 ? `${val}k` : `${val.toFixed(1)}k`;
                  }}
                  label={{ value: 'Oil (bbl/month)', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle' } }}
                />
                <YAxis
                  yAxisId="gas"
                  orientation="right"
                  domain={[0, 'auto']}
                  tickFormatter={(v) => {
                    if (v === 0) return '0k';
                    const val = v / 1000;
                    return val % 1 === 0 ? `${val}k` : `${val.toFixed(1)}k`;
                  }}
                  label={{ value: 'Gas (MCF/month)', angle: 90, position: 'insideRight', style: { textAnchor: 'middle' } }}
                />
                <Tooltip
                  labelFormatter={(value) => `Date: ${formatChartDate(value as number)}`}
                  formatter={(value: number, name: string) => {
                    if (name === 'BBLS_OIL_COND' || name === 'Forecast_Oil') {
                      return [value.toFixed(0), 'Barrels'];
                    }
                    if (name === 'MCF_GAS' || name === 'Forecast_Gas') {
                      return [value.toFixed(0), 'MCF'];
                    }
                    return [value.toFixed(0), name];
                  }}
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                />
                <Area
                  yAxisId="oil"
                  type="monotone"
                  dataKey="BBLS_OIL_COND"
                  stroke="#3b82f6"
                  fill="#3b82f6"
                  fillOpacity={0.2}
                  strokeWidth={2}
                  connectNulls={true}
                />
                <Area
                  yAxisId="gas"
                  type="monotone"
                  dataKey="MCF_GAS"
                  stroke="#22c55e"
                  fill="#22c55e"
                  fillOpacity={0.2}
                  strokeWidth={2}
                  connectNulls={true}
                />
                <Line
                  yAxisId={stream === 'gas' ? 'gas' : 'oil'}
                  type="monotone"
                  dataKey={stream === 'gas' ? 'Forecast_Gas' : 'Forecast_Oil'}
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
          <div className="flex-1 flex flex-col items-center justify-center text-gray-400 border-2 border-dashed rounded-lg bg-gray-50 m-4">
            <Activity className="w-12 h-12 mb-2 opacity-20" />
            <p>No production history available for this well.</p>
          </div>
        )}
      </div>
    </div>
  );
}
