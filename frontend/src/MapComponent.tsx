import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { Well } from './api/client';
import './Map.css';
import { useEffect } from 'react';
import { GisLayers } from './GisLayers';
import type { GisLayerState } from './GisLayers';

// Fix for default markers in React Leaflet
const defaultIcon = L.divIcon({
  className: 'custom-marker',
  html: '<div style="background-color: blue; width: 10px; height: 10px; border-radius: 50%;"></div>',
  iconSize: [10, 10],
  iconAnchor: [5, 5],
});

interface MapProps {
    wells: Well[];
    selectedWell: Well | null;
    onSelectWell: (well: Well) => void;
    gisLayers: GisLayerState;
}

// Component to recenter map when selected well changes
function Recenter({ lat, long }: { lat: number; long: number }) {
    const map = useMap();
    useEffect(() => {
        map.setView([lat, long], 14);
    }, [lat, long, map]);
    return null;
}

export function MapComponent({ wells, selectedWell, onSelectWell, gisLayers }: MapProps) {
    // Default center (Montana roughly)
    const center: [number, number] = [47.5, -109.5];
    const zoom = 7;

    return (
        <MapContainer center={center} zoom={zoom} scrollWheelZoom={true}>
            <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {wells.map((well) => (
                <Marker
                    key={well.API_WellNo}
                    position={[well.Lat, well.Long]}
                    icon={defaultIcon}
                    eventHandlers={{
                        click: () => onSelectWell(well),
                    }}
                >
                    <Popup>
                        <strong>API: {well.API_WellNo}</strong><br />
                        Lat: {well.Lat.toFixed(4)}<br />
                        Long: {well.Long.toFixed(4)}
                    </Popup>
                </Marker>
            ))}

            <GisLayers visible={gisLayers} />

            {selectedWell && <Recenter lat={selectedWell.Lat} long={selectedWell.Long} />}
        </MapContainer>
    );
}
