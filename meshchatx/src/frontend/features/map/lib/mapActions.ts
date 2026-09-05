// SPDX-License-Identifier: 0BSD

import { getLength, getArea } from "ol/sphere";

export async function resolveMyLocationWgs84(ctx: {
    config?: {
        location_source?: string;
        lxmf_address_hash?: string;
        identity_hash?: string;
    };
    telemetryList?: any[];
}): Promise<{ lon: number; lat: number } | null> {
    const cfg = ctx.config || {};
    const lx = cfg.lxmf_address_hash;
    const id = cfg.identity_hash;
    const list = ctx.telemetryList || [];

    if (lx) {
        const match = list.find((t: any) => t.destination_hash === lx);
        const loc = match?.telemetry?.location;
        if (loc && typeof loc.longitude === "number" && typeof loc.latitude === "number") {
            return { lon: loc.longitude, lat: loc.latitude };
        }
    }

    if (id) {
        const match = list.find((t: any) => t.destination_hash === id);
        const loc = match?.telemetry?.location;
        if (loc && typeof loc.longitude === "number" && typeof loc.latitude === "number") {
            return { lon: loc.longitude, lat: loc.latitude };
        }
    }

    if (typeof navigator !== "undefined" && navigator.geolocation) {
        try {
            const pos = await new Promise<GeolocationPosition>((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000 });
            });
            return { lon: pos.coords.longitude, lat: pos.coords.latitude };
        } catch {
            return null;
        }
    }

    return null;
}

export async function handleRemoteOverlaysChanged(
    ctx: {
        map?: any;
        remoteOverlayLoadGeneration: number;
        remoteOverlayLayers: Record<string, any>;
        removeRemoteOverlayLayer: (id: string) => void;
        ensureRemoteOverlayLayer: (overlay: any) => Promise<void>;
    },
    overlays: any[]
): Promise<void> {
    const list = overlays || [];
    const loadGen = ++ctx.remoteOverlayLoadGeneration;
    const wantedIds = new Set(list.filter((o) => o.visible).map((o) => String(o.id)));

    for (const existingId of Object.keys(ctx.remoteOverlayLayers)) {
        if (!wantedIds.has(existingId)) {
            ctx.removeRemoteOverlayLayer(existingId);
        }
    }

    for (const overlay of list) {
        if (!overlay.visible) continue;
        await ctx.ensureRemoteOverlayLayer(overlay);
        if (ctx.remoteOverlayLoadGeneration !== loadGen) {
            ctx.removeRemoteOverlayLayer(String(overlay.id));
        }
    }
}

export function formatLength(line: any): string {
    const length = getLength(line);
    let output: string;
    let imperialOutput: string;

    if (length > 100) {
        output = Math.round((length / 1000) * 100) / 100 + " km";
    } else {
        output = Math.round(length * 100) / 100 + " m";
    }

    const feet = length * 3.28084;
    if (feet > 5280) {
        const miles = length * 0.000621371;
        imperialOutput = Math.round(miles * 100) / 100 + " mi";
    } else {
        imperialOutput = Math.round(feet * 100) / 100 + " ft";
    }

    return `${output}<br/><span class="text-[10px] opacity-80">${imperialOutput}</span>`;
}

export function formatArea(polygon: any): string {
    const area = getArea(polygon);
    let output: string;
    let imperialOutput: string;

    if (area > 10000) {
        output = Math.round((area / 1000000) * 100) / 100 + " km²";
    } else {
        output = Math.round(area * 100) / 100 + " m²";
    }

    const sqFeet = area * 10.7639;
    if (sqFeet > 27878400) {
        const sqMiles = area * 0.000000386102;
        imperialOutput = Math.round(sqMiles * 100) / 100 + " mi²";
    } else {
        imperialOutput = Math.round(sqFeet * 100) / 100 + " ft²";
    }

    return `${output}<br/><span class="text-[10px] opacity-80">${imperialOutput}</span>`;
}

export function calculateAzimuth(
    lon1: number,
    lat1: number,
    lon2: number,
    lat2: number
): { deg: number; cardinal: string } {
    const toRad = (d: number) => (d * Math.PI) / 180;
    const toDeg = (r: number) => (r * 180) / Math.PI;

    const phi1 = toRad(lat1);
    const phi2 = toRad(lat2);
    const deltaLambda = toRad(lon2 - lon1);

    const y = Math.sin(deltaLambda) * Math.cos(phi2);
    const x = Math.cos(phi1) * Math.sin(phi2) - Math.sin(phi1) * Math.cos(phi2) * Math.cos(deltaLambda);

    let deg = (toDeg(Math.atan2(y, x)) + 360) % 360;
    deg = Math.round(deg * 10) / 10;

    const cardinals = [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    ];
    const index = Math.round(deg / 22.5) % 16;
    return { deg, cardinal: cardinals[index] };
}
