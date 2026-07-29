import { useState } from 'react';
import { Layers, Loader2 } from 'lucide-react';
import type { GisLayerState } from './GisLayers';

interface LayerToggleProps {
    layers: GisLayerState;
    onToggle: (key: keyof GisLayerState) => void;
    featureCounts: Record<string, number>;
}

const LAYER_DEFS: { key: keyof GisLayerState; label: string; color: string; description: string }[] = [
    { key: 'paths', label: 'Well Paths', color: '#ea580c', description: 'Horizontal wellbore trajectories' },
    { key: 'fields', label: 'Fields', color: '#16a34a', description: 'Production field boundaries' },
    { key: 'units', label: 'Units', color: '#7c3aed', description: 'Enhanced recovery units' },
];

function Toggle({ enabled, color }: { enabled: boolean; color: string }) {
    return (
        <div
            className={`relative w-11 h-6 rounded-full transition-colors duration-200 ease-in-out shrink-0 ${enabled ? '' : 'bg-gray-300'}`}
            style={enabled ? { backgroundColor: color } : undefined}
        >
            <div
                className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow-md transition-transform duration-200 ease-in-out ${enabled ? 'translate-x-5' : 'translate-x-0'}`}
            />
        </div>
    );
}

export function LayerToggle({ layers, onToggle, featureCounts }: LayerToggleProps) {
    const [expanded, setExpanded] = useState(true);

    return (
        <div className="backdrop-blur-md bg-white/80 rounded-2xl shadow-lg border border-white/50 overflow-hidden transition-all duration-300">
            <button
                onClick={() => setExpanded(!expanded)}
                className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/60 transition-colors"
            >
                <div className="flex items-center gap-2.5">
                    <div className="p-1.5 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 shadow-sm">
                        <Layers className="w-4 h-4 text-white" />
                    </div>
                    <span className="font-semibold text-sm text-gray-800">Map Overlays</span>
                </div>
                <svg
                    className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
            </button>

            <div className={`transition-all duration-300 ease-in-out overflow-hidden ${expanded ? 'max-h-80 opacity-100' : 'max-h-0 opacity-0'}`}>
                <div className="px-4 pb-3 space-y-2">
                    {LAYER_DEFS.map(({ key, label, color, description }) => (
                        <button
                            key={key}
                            onClick={() => onToggle(key)}
                            className="w-full flex items-center gap-3 p-2.5 rounded-xl hover:bg-gray-50/80 transition-colors group text-left"
                        >
                            <Toggle enabled={layers[key]} color={color} />
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                    <div
                                        className="w-2 h-2 rounded-full shrink-0 transition-opacity duration-200"
                                        style={{ backgroundColor: color, opacity: layers[key] ? 1 : 0.3 }}
                                    />
                                    <span className={`text-sm font-medium transition-colors ${layers[key] ? 'text-gray-800' : 'text-gray-400'}`}>
                                        {label}
                                    </span>
                                </div>
                                <p className={`text-xs mt-0.5 transition-colors ${layers[key] ? 'text-gray-500' : 'text-gray-300'}`}>
                                    {description}
                                </p>
                            </div>
                            <div
                                className={`text-xs font-mono font-medium px-2 py-0.5 rounded-full transition-all duration-200 ${layers[key]
                                        ? 'text-gray-600 bg-gray-100'
                                        : 'text-gray-300 bg-transparent'
                                    }`}
                            >
                                {featureCounts[key] !== undefined
                                    ? featureCounts[key].toLocaleString()
                                    : <Loader2 className="w-3 h-3 animate-spin" />}
                            </div>
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
}
