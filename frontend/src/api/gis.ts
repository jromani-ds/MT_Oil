const GIS_BASE_URL = import.meta.env.VITE_GIS_BASE_URL || '';

export interface GisLayerUrls {
    well_paths: string;
    fields: string;
    units: string;
}

function defaultUrls(): GisLayerUrls {
    const base = GIS_BASE_URL;
    return {
        well_paths: `${base}well_paths.json`,
        fields: `${base}fields.json`,
        units: `${base}units.json`,
    };
}

let cachedUrls: GisLayerUrls | null = null;

export function getGisLayerUrls(): GisLayerUrls {
    if (!cachedUrls) {
        cachedUrls = defaultUrls();
    }
    return cachedUrls;
}

export async function fetchGeoJson(url: string): Promise<GeoJSON.FeatureCollection | null> {
    if (!url.startsWith('http')) {
        return null;
    }
    try {
        const response = await fetch(url);
        if (!response.ok) {
            console.warn(`GIS fetch failed for ${url}: ${response.status}`);
            return null;
        }
        return await response.json();
    } catch (e) {
        console.warn(`GIS fetch error for ${url}:`, e);
        return null;
    }
}
