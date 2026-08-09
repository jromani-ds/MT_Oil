import type { Well, FilterOptions, FilterParams } from '../api/client';
import type { GisLayerState } from '../GisLayers';
import { LayerToggle } from '../LayerToggle';
import { Filter } from 'lucide-react';
import { formatAPI, formatCoordinate } from '../utils/format';

interface MapSidebarProps {
  filterOptions: FilterOptions | null;
  filters: FilterParams;
  showFilters: boolean;
  selectedWell: Well | null;
  gisLayers: GisLayerState;
  gisFeatureCounts: Record<string, number>;
  onToggleFilters: () => void;
  onFilterChange: (filters: FilterParams) => void;
  onToggleGisLayer: (key: keyof GisLayerState) => void;
}

export function MapSidebar({
  filterOptions,
  filters,
  showFilters,
  selectedWell,
  gisLayers,
  gisFeatureCounts,
  onToggleFilters,
  onFilterChange,
  onToggleGisLayer,
}: MapSidebarProps) {
  return (
    <div id="map-sidebar" className="w-72 lg:w-80 p-4 flex flex-col gap-4 overflow-y-auto border-r border-gray-200 bg-white min-h-0">
      {/* Filters Card */}
      <div className="bg-gray-50 rounded-lg shadow-sm p-4 border border-gray-200">
        <div
className="flex justify-between items-center cursor-pointer mb-2 pr-4"
          onClick={onToggleFilters}
        >
          <h3 className="font-bold text-gray-700 flex items-center gap-2">
            <Filter className="w-4 h-4" /> Filter Wells
          </h3>
            <button type="button" className="px-2.5 py-1 text-xs font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded-md transition-colors">{showFilters ? 'Hide' : 'Show'}</button>
        </div>

        {showFilters && filterOptions && (
          <div className="text-sm">
            <div className="flex flex-col gap-1.5 mb-4">
              <label className="text-sm font-medium text-gray-700 mb-1" htmlFor="well-type">Well Type</label>
              <select
                id="well-type"
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-gray-700 bg-white appearance-none"
                value={filters.wellType || ''}
                onChange={(e) => onFilterChange({ ...filters, wellType: e.target.value || undefined })}
              >
                <option value="">All Types</option>
                {filterOptions.well_types.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div className="flex flex-col gap-1.5 mb-4">
              <label className="text-sm font-medium text-gray-700 mb-1" htmlFor="formation">Formation</label>
              <select
                id="formation"
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-gray-700 bg-white appearance-none"
                value={filters.formation || ''}
                onChange={(e) => onFilterChange({ ...filters, formation: e.target.value || undefined })}
              >
                <option value="">All Formations</option>
                {filterOptions.formations.map(f => <option key={f} value={f}>{f}</option>)}
              </select>
            </div>
            <div className="flex flex-col gap-1.5 mb-4">
              <label className="text-sm font-medium text-gray-700 mb-1" htmlFor="trajectory">Trajectory</label>
              <select
                id="trajectory"
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-gray-700 bg-white appearance-none"
                value={filters.slant || ''}
                onChange={(e) => onFilterChange({ ...filters, slant: e.target.value || undefined })}
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
          <p className="text-xs text-blue-700 font-mono">{formatAPI(selectedWell.API_WellNo)}</p>
          <p className="text-xs text-blue-600 mt-1">
            Lat: {formatCoordinate(selectedWell.Lat)}, Long: {formatCoordinate(selectedWell.Long)}
          </p>
        </div>
      )}

      <LayerToggle
        layers={gisLayers}
        onToggle={onToggleGisLayer}
        featureCounts={gisFeatureCounts}
      />
    </div>
  );
}
