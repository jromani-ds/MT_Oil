import { useState } from 'react';
import type { Well, FilterOptions, FilterParams } from '../api/client';
import { getWells } from '../api/client';
import type { GisLayerState } from '../GisLayers';
import { LayerToggle } from '../LayerToggle';
import { Filter, Search } from 'lucide-react';
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
  onSelectWell?: (well: Well) => void;
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
  onSelectWell,
}: MapSidebarProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Well[]>([]);
  const [searching, setSearching] = useState(false);

  const handleSearch = async () => {
    const q = searchQuery.trim();
    if (!q) return;
    setSearching(true);
    try {
      const results = await getWells({ search: q, limit: 8, hasProduction: false });
      setSearchResults(results);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch();
  };

  const handleSelect = (well: Well) => {
    setSearchResults([]);
    setSearchQuery('');
    onSelectWell?.(well);
  };

  return (
    <div id="map-sidebar" className="w-72 lg:w-80 p-4 flex flex-col gap-4 overflow-y-auto border-r border-gray-200 bg-white min-h-0">
      {/* Search Card */}
      <div className="bg-gray-50 rounded-lg shadow-sm p-4 border border-gray-200">
        <h3 className="font-bold text-gray-700 flex items-center gap-2 mb-2">
          <Search className="w-4 h-4" /> Find Well
        </h3>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="API number..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1 border border-gray-300 rounded px-2 py-1.5 text-sm text-gray-700 bg-white"
          />
          <button
            onClick={handleSearch}
            disabled={searching}
            className="px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {searching ? '...' : 'Go'}
          </button>
        </div>
        {searchResults.length > 0 && (
          <ul className="mt-2 border border-gray-200 rounded bg-white divide-y divide-gray-100 max-h-48 overflow-y-auto">
            {searchResults.map((w) => (
              <li key={w.API_WellNo}>
                <button
                  onClick={() => handleSelect(w)}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-blue-50 transition-colors"
                >
                  <span className="font-mono text-gray-800">{formatAPI(w.API_WellNo)}</span>
                  {w.Type && <span className="ml-2 text-xs text-gray-500">({w.Type})</span>}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Filters Card */}
      <div className="bg-gray-50 rounded-lg shadow-sm p-4 border border-gray-200">
        <div
className="flex justify-between items-center cursor-pointer mb-2 pr-3"
          onClick={onToggleFilters}
        >
          <h3 className="font-bold text-gray-700 flex items-center gap-2">
            <Filter className="w-4 h-4" /> Filter Wells
          </h3>
            <button type="button" className="px-2.5 py-1 text-xs font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded-md transition-colors">{showFilters ? 'Hide' : 'Show'}</button>
        </div>

        {showFilters && filterOptions && (
          <div className="grid grid-cols-1 gap-3 text-sm">
            <div>
<label className="block text-xs font-semibold text-gray-500 mb-2" htmlFor="well-type">Well Type</label>
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
            <div>
<label className="block text-xs font-semibold text-gray-500 mb-2" htmlFor="formation">Formation</label>
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
            <div>
<label className="block text-xs font-semibold text-gray-500 mb-2" htmlFor="trajectory">Trajectory</label>
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
