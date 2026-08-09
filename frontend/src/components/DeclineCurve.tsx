import type { ProductionRecord, DeclineResponse, Well } from '../api/client';
import { Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ComposedChart, Area } from 'recharts';
import { Activity, TrendingDown, Loader2 } from 'lucide-react';
import { formatCoordinate, formatYear, formatChartDate } from '../utils/format';

type ChartPoint = Partial<ProductionRecord> & { Forecast_Oil?: number; dateVal: number };

function buildChartData(production: ProductionRecord[], prediction: DeclineResponse | null): ChartPoint[] {
  const data: ChartPoint[] = production.map(p => ({
    ...p,
    dateVal: new Date(p.Rpt_Date).getTime(),
  }));

  if (prediction) {
    const lastDate = production.length > 0
      ? new Date(production[production.length - 1].Rpt_Date)
      : new Date();

    prediction.forecast.production.forEach((val, idx) => {
      const d = new Date(lastDate);
      d.setMonth(d.getMonth() + idx + 1);
      data.push({
        Rpt_Date: d.toISOString().split('T')[0],
        dateVal: d.getTime(),
        Forecast_Oil: val,
      });
    });
  }

  return data;
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

      {/* Chart */}
      <div className="flex-1 bg-white shadow-md flex flex-col m-4 rounded-lg overflow-hidden">
        <div className="flex justify-between items-center px-4 py-3 flex-shrink-0 border-b border-gray-100">
          <h3 className="font-semibold text-lg text-gray-700 flex items-center gap-2">
            <Activity className="w-5 h-5" /> Production Profile
            {prediction && (
              <span className="ml-3 bg-blue-100 text-blue-800 text-xs font-semibold px-3 py-1 rounded-full uppercase tracking-wide">
                DCA Method: {prediction.fit.method}
              </span>
            )}
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
          <div className="flex-1 w-full p-2">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.1} vertical={false} />
                <XAxis
                  dataKey="dateVal"
                  type="number"
                  scale="time"
                  domain={['dataMin', 'dataMax']}
                  tickFormatter={formatYear}
                  interval="preserveStartEnd"
                  minTickGap={50}
                  tick={{ fontSize: 12 }}
                />
                <YAxis
                  tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                  label={{ value: 'Oil (bbl/month)', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle' } }}
                />
                <Tooltip
                  labelFormatter={(value) => `Date: ${formatChartDate(value as number)}`}
                  formatter={(value: number) => [value.toFixed(0), 'Barrels']}
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                />
                <Area
                  type="monotone"
                  dataKey="BBLS_OIL_COND"
                  stroke="#3b82f6"
                  fill="#3b82f6"
                  fillOpacity={0.2}
                  strokeWidth={2}
                  connectNulls={true}
                />
                <Line
                  type="monotone"
                  dataKey="Forecast_Oil"
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
