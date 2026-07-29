import { Layers, Loader2 } from 'lucide-react';
import type { GisLayerState } from './GisLayers';

interface LayerToggleProps {
    layers: GisLayerState;
    onToggle: (key: keyof GisLayerState) => void;
    featureCounts: Record<string, number>;
}

const LAYER_DEFS: { key: keyof GisLayerState; label: string; color: string; }[] = [
    { key: 'wells', label: 'Well Surfaces', color: '#1d4ed8' },
    { key: 'paths', label: 'Horizontal Paths', color: '#ea580c' },
    { key: 'fields', label: 'Production Fields', color: '#16a34a' },
    { key: 'units', label: 'Recovery Units', color: '#7c3aed' },
];

export function LayerToggle({ layers, onToggle, featureCounts }: LayerToggleProps) {
    return (
        <div className="bg-gray-50 rounded-lg shadow-sm p-4 border border-gray-200">
            <h3 className="font-bold text-gray-700 flex items-center gap-2 mb-3">
                <Layers className="w-4 h-4" /> GIS Layers
            </h3>
            <div className="space-y-2">
                {LAYER_DEFS.map(({ key, label, color }) => (
                    <label
                        key={key}
                        className="flex items-center gap-3 cursor-pointer group"
                    >
                        <div className="relative flex items-center">
                            <input
                                type="checkbox"
                                checked={layers[key]}
                                onChange={() => onToggle(key)}
                                className="sr-only"
                            />
                            <div
                                className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${layers[key]
                                        ? 'border-transparent'
                                        : 'border-gray-300 group-hover:border-gray-400'
                                    }`}
                                style={layers[key] ? { backgroundColor: color } : undefined}
                            >
                                {layers[key] && (
                                    <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                    </svg>
                                )}
                            </div>
                        </div>
                        <span className="text-sm text-gray-700 flex-1">{label}</span>
                        <span className="text-xs text-gray-400">
                            {featureCounts[key] !== undefined
                                ? featureCounts[key].toLocaleString()
                                : <Loader2 className="w-3 h-3 animate-spin inline" />}
                        </span>
                    </label>
                ))}
            </div>
        </div>
    );
}
