import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import type { Well } from './api/client';
import './Map.css';
import { useEffect } from 'react';

interface MapProps {
    wells: Well[];
    selectedWell: Well | null;
    onSelectWell: (well: Well) => void;
}

// Component to recenter map when selected well changes
function Recenter({ lat, long }: { lat: number; long: number }) {
    const map = useMap();
    useEffect(() => {
        map.setView([lat, long], 14);
    }, [lat, long, map]);
    return null;
}

export function MapComponent({ wells, selectedWell, onSelectWell }: MapProps) {
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
                <CircleMarker
                    key={well.API_WellNo}
                    center={[well.Lat, well.Long]}
                    pathOptions={{
                        color: selectedWell?.API_WellNo === well.API_WellNo ? 'red' : 'blue',
                        fillColor: selectedWell?.API_WellNo === well.API_WellNo ? '#ff0000' : '#0000ff',
                        fillOpacity: 0.6
                    }}
                    radius={selectedWell?.API_WellNo === well.API_WellNo ? 8 : 4}
                    eventHandlers={{
                        click: () => onSelectWell(well),
                    }}
                >
                    <Popup>
                        <strong>API: {well.API_WellNo}</strong><br />
                        Lat: {well.Lat}<br />
                        Long: {well.Long}
                    </Popup>
                </CircleMarker>
            ))}

            {selectedWell && <Recenter lat={selectedWell.Lat} long={selectedWell.Long} />}
        </MapContainer>
    );
}
