import { useState } from 'react';
import { Layers, Loader2, Eye, EyeOff } from 'lucide-react';
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
            className={`relative w-10 h-5 rounded-full transition-all duration-300 ease-in-out shrink-0 shadow-inner ${enabled ? '' : 'bg-gray-200'}`}
            style={enabled ? { backgroundColor: color } : undefined}
        >
            <div
                className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow-md transition-all duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)] ${enabled ? 'left-[21px]' : 'left-0.5'}`}
            />
        </div>
    );
}

export function LayerToggle({ layers, onToggle, featureCounts }: LayerToggleProps) {
    const [expanded, setExpanded] = useState(true);
    const activeCount = Object.values(layers).filter(Boolean).length;

    return (
        <div className="backdrop-blur-md bg-white/85 rounded-2xl shadow-lg border border-white/50 overflow-hidden transition-all duration-300">
            <button
                onClick={() => setExpanded(!expanded)}
                className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/60 transition-colors"
            >
                <div className="flex items-center gap-2.5">
                    <div className="p-1.5 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 shadow-sm">
                        <Layers className="w-4 h-4 text-white" />
                    </div>
                    <span className="font-semibold text-sm text-gray-800">Map Overlays</span>
                    {activeCount > 0 && (
                        <span className="text-[10px] font-bold text-white px-1.5 py-0.5 rounded-full bg-gray-500/70">
                            {activeCount}
                        </span>
                    )}
                </div>
                <svg
                    className={`w-3 h-3 text-gray-400 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
            </button>

            <div
                className={`transition-all duration-300 ease-in-out overflow-hidden ${expanded ? 'max-h-80 opacity-100' : 'max-h-0 opacity-0'}`}
            >
                <div className="px-3 pb-3 space-y-1.5">
                    {LAYER_DEFS.map(({ key, label, color, description }) => {
                        const active = layers[key];
                        return (
                            <button
                                key={key}
                                onClick={() => onToggle(key)}
                                className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all duration-200 text-left relative overflow-hidden ${active
                                    ? 'shadow-sm border border-white/60'
                                    : 'hover:bg-gray-50/60 border border-transparent'
                                    }`}
                                style={active ? { backgroundColor: `${color}0d`, boxShadow: `0 0 0 1px ${color}20` } : undefined}
                            >
                                {active && (
                                    <div
                                        className="absolute left-0 top-1 bottom-1 w-[3px] rounded-r-full"
                                        style={{ backgroundColor: color }}
                                    />
                                )}
                                <div className="flex-1 min-w-0 pl-1">
                                    <div className="flex items-center gap-2">
                                        <div
                                            className={`w-2.5 h-2.5 rounded-full shrink-0 transition-all duration-300 ${active ? '' : 'grayscale opacity-30'}`}
                                            style={{ backgroundColor: color }}
                                        />
                                        <span
                                            className={`text-sm transition-all duration-200 ${active ? 'font-bold text-gray-900' : 'font-medium text-gray-400'}`}
                                        >
                                            {label}
                                        </span>
                                    </div>
                                    <p
                                        className={`text-[11px] mt-0.5 transition-all duration-200 ${active ? 'text-gray-500' : 'text-gray-300'}`}
                                    >
                                        {description}
                                    </p>
                                </div>
                                <div className="flex items-center gap-2.5">
                                    <div
                                        className={`text-[11px] font-mono font-semibold px-2 py-0.5 rounded-md transition-all duration-200 ${active
                                            ? 'text-gray-600 bg-gray-100/80'
                                            : 'text-gray-300 bg-transparent'
                                            }`}
                                    >
                                        {featureCounts[key] !== undefined
                                            ? featureCounts[key].toLocaleString()
                                            : <Loader2 className="w-3 h-3 animate-spin" />}
                                    </div>
                                    <div className="flex items-center gap-1.5">
                                        {active ? (
                                            <Eye className="w-3.5 h-3.5 text-gray-400" />
                                        ) : (
                                            <EyeOff className="w-3.5 h-3.5 text-gray-300" />
                                        )}
                                        <Toggle enabled={active} color={color} />
                                    </div>
                                </div>
                            </button>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
