import { GeoJSON } from 'react-leaflet';
import L from 'leaflet';
import { useEffect, useState, useRef } from 'react';
import { fetchGeoJson, getGisLayerUrls } from './api/gis';
import './GisLayers.css';

export interface GisLayerState {
    wells: boolean;
    paths: boolean;
    fields: boolean;
    units: boolean;
}

interface GisLayersProps {
    visible: GisLayerState;
}

interface GeoData {
    data: GeoJSON.FeatureCollection | null;
    featureCount: number;
}

function wellPointToLayer(_feature: unknown, latlng: L.LatLng): L.CircleMarker {
    return L.circleMarker(latlng, {
        radius: 4,
        fillColor: '#1d4ed8',
        color: '#1e3a8a',
        weight: 1,
        opacity: 0.8,
        fillOpacity: 0.7,
    });
}

function wellPathStyle(): L.PathOptions {
    return {
        color: '#ea580c',
        weight: 2.5,
        opacity: 0.8,
    };
}

function fieldStyle(): L.PathOptions {
    return {
        fillColor: '#16a34a',
        fillOpacity: 0.15,
        color: '#15803d',
        weight: 2,
        opacity: 0.8,
    };
}

function unitStyle(): L.PathOptions {
    return {
        fillColor: '#7c3aed',
        fillOpacity: 0.12,
        color: '#6d28d9',
        weight: 2,
        dashArray: '6 4',
        opacity: 0.8,
    };
}

function wellPopup(feature: GeoJSON.GeoJsonProperties): string {
    const props = feature || {};
    return `
        <div class="gis-popup">
            <strong>Well Surface</strong><br/>
            API: ${props.API_WellNo || props.api_wellno || props.API_NUMBER || 'N/A'}<br/>
            ${props.WellName || props.well_name || props.NAME ? `Name: ${props.WellName || props.well_name || props.NAME}<br/>` : ''}
            ${props.Operator || props.operator || props.OPERATOR ? `Operator: ${props.Operator || props.operator || props.OPERATOR}<br/>` : ''}
            ${props.Type || props.type ? `Type: ${props.Type || props.type}<br/>` : ''}
            ${props.TD || props.td ? `TD: ${props.TD || props.td} ft` : ''}
        </div>
    `;
}

function pathPopup(feature: GeoJSON.GeoJsonProperties): string {
    const props = feature || {};
    return `
        <div class="gis-popup">
            <strong>Well Path</strong><br/>
            API: ${props.API_WellNo || props.api_wellno || props.API_NUMBER || 'N/A'}<br/>
            ${props.MD || props.md || props.MeasuredDepth ? `MD: ${props.MD || props.md || props.MeasuredDepth} ft<br/>` : ''}
            ${props.LateralLength || props.lateral_length ? `Lateral: ${props.LateralLength || props.lateral_length} ft<br/>` : ''}
        </div>
    `;
}

function fieldPopup(feature: GeoJSON.GeoJsonProperties): string {
    const props = feature || {};
    return `
        <div class="gis-popup">
            <strong>Production Field</strong><br/>
            ${props.FieldName || props.field_name || props.NAME || props.Field ? `Name: ${props.FieldName || props.field_name || props.NAME || props.Field}<br/>` : ''}
            ${props.DiscoveryYear || props.discovery_year || props.YEAR ? `Discovery: ${props.DiscoveryYear || props.discovery_year || props.YEAR}<br/>` : ''}
            ${props.Status || props.status ? `Status: ${props.Status || props.status}` : ''}
        </div>
    `;
}

function unitPopup(feature: GeoJSON.GeoJsonProperties): string {
    const props = feature || {};
    return `
        <div class="gis-popup">
            <strong>Recovery Unit</strong><br/>
            ${props.UnitName || props.unit_name || props.NAME || props.Unit ? `Name: ${props.UnitName || props.unit_name || props.NAME || props.Unit}<br/>` : ''}
            ${props.UnitType || props.unit_type || props.TYPE ? `Type: ${props.UnitType || props.unit_type || props.TYPE}<br/>` : ''}
            ${props.Formation || props.formation || props.FORMATION ? `Formation: ${props.Formation || props.formation || props.FORMATION}<br/>` : ''}
            ${props.Status || props.status ? `Status: ${props.Status || props.status}` : ''}
        </div>
    `;
}

function useGeoJsonData(layerKey: keyof GisLayerState, visible: boolean): GeoData {
    const [data, setData] = useState<GeoData>({ data: null, featureCount: 0 });
    const prevVisible = useRef(false);

    useEffect(() => {
        if (visible && !prevVisible.current) {
            prevVisible.current = true;
            let cancelled = false;
            const urls = getGisLayerUrls();
            const urlMap: Record<keyof GisLayerState, string> = {
                wells: urls.wells_surfaces,
                paths: urls.well_paths,
                fields: urls.fields,
                units: urls.units,
            };
            const url = urlMap[layerKey];
            if (!url) return;

            fetchGeoJson(url).then((geojson) => {
                if (cancelled) return;
                if (geojson) {
                    setData({
                        data: geojson,
                        featureCount: geojson.features?.length || 0,
                    });
                }
            });

            return () => { cancelled = true; };
        } else if (!visible && prevVisible.current) {
            prevVisible.current = false;
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setData({ data: null, featureCount: 0 });
        }
    }, [layerKey, visible]);

    return data;
}

function WellSurfacesLayer() {
    const { data } = useGeoJsonData('wells', true);
    if (!data) return null;
    return (
        <GeoJSON
            key="wells-surfaces"
            data={data}
            pointToLayer={wellPointToLayer}
            onEachFeature={(feature, layer) => {
                layer.bindPopup(wellPopup(feature.properties));
            }}
        />
    );
}

function WellPathsLayer() {
    const { data } = useGeoJsonData('paths', true);
    if (!data) return null;
    return (
        <GeoJSON
            key="well-paths"
            data={data}
            style={wellPathStyle}
            onEachFeature={(feature, layer) => {
                layer.bindPopup(pathPopup(feature.properties));
            }}
        />
    );
}

function FieldsLayer() {
    const { data } = useGeoJsonData('fields', true);
    if (!data) return null;
    return (
        <GeoJSON
            key="fields"
            data={data}
            style={fieldStyle}
            onEachFeature={(feature, layer) => {
                layer.bindPopup(fieldPopup(feature.properties));
            }}
        />
    );
}

function UnitsLayer() {
    const { data } = useGeoJsonData('units', true);
    if (!data) return null;
    return (
        <GeoJSON
            key="units"
            data={data}
            style={unitStyle}
            onEachFeature={(feature, layer) => {
                layer.bindPopup(unitPopup(feature.properties));
            }}
        />
    );
}

export function GisLayers({ visible }: GisLayersProps) {
    return (
        <>
            {visible.wells && <WellSurfacesLayer />}
            {visible.paths && <WellPathsLayer />}
            {visible.fields && <FieldsLayer />}
            {visible.units && <UnitsLayer />}
        </>
    );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useGisFeatureCounts(visible: GisLayerState): Record<string, number> {
    const wells = useGeoJsonData('wells', visible.wells);
    const paths = useGeoJsonData('paths', visible.paths);
    const fields = useGeoJsonData('fields', visible.fields);
    const units = useGeoJsonData('units', visible.units);

    return {
        wells: wells.featureCount,
        paths: paths.featureCount,
        fields: fields.featureCount,
        units: units.featureCount,
    };
}
