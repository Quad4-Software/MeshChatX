// SPDX-License-Identifier: 0BSD

import { Style, Text, Fill, Stroke, Circle as CircleStyle, Icon } from "ol/style";

export const DEFAULT_PEER_FACE = "#3730a3";
export const DEFAULT_PEER_GLYPH = "#ffffff";
export const DEFAULT_DISCOVERED_FACE = "#059669";
export const DEFAULT_MAP_PIN_PATH =
    "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7Zm0 11a2 2 0 1 1 0-4 2 2 0 0 1 0 4Z";
export const MARKER_LABEL_MIN_ZOOM = 12;
export const BADGE_SCALE_NORMAL = 1;
export const BADGE_SCALE_HOVER = 1.12;

const STALE_FACE = "#64748b";
const STALE_GLYPH = "#e2e8f0";

interface BadgeSvgOptions {
    face?: string;
    glyph?: string;
    pathD?: string;
    stale?: boolean;
    tracking?: boolean;
}

interface PeerBadgeStyleOptions {
    face?: string;
    glyph?: string;
    iconColor?: string;
    bgColor?: string;
    pathD?: string;
    iconPath?: string;
    label?: string;
    showLabel?: boolean;
    isStale?: boolean;
    isTracking?: boolean;
    scale?: number;
}

interface ClusterStyleOptions {
    count?: number;
    hovered?: boolean;
}

interface ClusterBand {
    bandId: string;
    radius: number;
    face: string;
}

function parseHexColor(color: string): { r: number; g: number; b: number } | null {
    if (typeof color !== "string") return null;
    let hex = color.trim();
    if (hex.startsWith("#")) hex = hex.slice(1);
    if (hex.length === 3) {
        hex = hex
            .split("")
            .map((c) => c + c)
            .join("");
    }
    if (!/^[0-9a-fA-F]{6}$/.test(hex)) return null;
    return {
        r: parseInt(hex.slice(0, 2), 16) / 255,
        g: parseInt(hex.slice(2, 4), 16) / 255,
        b: parseInt(hex.slice(4, 6), 16) / 255,
    };
}

export function relativeLuminance(color: string): number {
    const rgb = parseHexColor(color);
    if (!rgb) return 0.5;
    const lin = (c: number): number => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
    return 0.2126 * lin(rgb.r) + 0.7152 * lin(rgb.g) + 0.0722 * lin(rgb.b);
}

export function contrastRatio(a: string, b: string): number {
    const L1 = relativeLuminance(a);
    const L2 = relativeLuminance(b);
    const lighter = Math.max(L1, L2);
    const darker = Math.min(L1, L2);
    return (lighter + 0.05) / (darker + 0.05);
}

export function contrastGlyphColor(bg: string, preferred?: string): string {
    const white = "#ffffff";
    const ink = "#0f172a";
    if (preferred && contrastRatio(preferred, bg) >= 3) {
        return preferred;
    }
    return relativeLuminance(bg) > 0.45 ? ink : white;
}

export function shouldShowMarkerLabel({
    zoom,
    hovered = false,
    selected = false,
}: { zoom?: number; hovered?: boolean; selected?: boolean } = {}): boolean {
    if (hovered || selected) return true;
    return Number.isFinite(zoom) && (zoom as number) >= MARKER_LABEL_MIN_ZOOM;
}

export function encodeSvgDataUrl(svg: string): string {
    const bytes = new TextEncoder().encode(svg);
    let binary = "";
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
        binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
    }
    return "data:image/svg+xml;base64," + btoa(binary);
}

export function buildPeerBadgeSvg({
    face,
    glyph,
    pathD = DEFAULT_MAP_PIN_PATH,
    stale = false,
    tracking = false,
}: BadgeSvgOptions = {}): string {
    const faceColor = stale ? STALE_FACE : face || DEFAULT_PEER_FACE;
    const glyphColor = stale ? STALE_GLYPH : glyph || DEFAULT_PEER_GLYPH;
    const opacity = stale ? "0.72" : "1";
    const showPulse = tracking && !stale;
    const size = showPulse ? 48 : 40;
    const cx = size / 2;
    const cy = size / 2;
    const r = showPulse ? 12 : 11;

    const pulse = showPulse
        ? `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="#38bdf8" stroke-width="2">
            <animate attributeName="r" from="${r}" to="${r + 8}" dur="1.5s" repeatCount="indefinite" />
            <animate attributeName="stroke-opacity" from="0.9" to="0" dur="1.5s" repeatCount="indefinite" />
          </circle>
          <circle cx="${cx}" cy="${cy}" r="${r - 1}" fill="#38bdf8" fill-opacity="0.18">
            <animate attributeName="r" from="${r - 2}" to="${r + 3}" dur="1.5s" repeatCount="indefinite" />
            <animate attributeName="fill-opacity" from="0.22" to="0" dur="1.5s" repeatCount="indefinite" />
          </circle>`
        : "";

    return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
  <g opacity="${opacity}">
    <circle class="badge-shadow" cx="${cx + 0.6}" cy="${cy + 1.1}" r="${r + 1}" fill="rgba(15,23,42,0.28)"/>
    ${pulse}
    <circle class="badge-rim-dark" cx="${cx}" cy="${cy}" r="${r}" fill="${faceColor}" stroke="rgba(15,23,42,0.78)" stroke-width="3"/>
    <circle class="badge-rim-light" cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="rgba(255,255,255,0.92)" stroke-width="1.6"/>
    <g transform="translate(${cx},${cy}) scale(0.52) translate(-12,-12)">
      <path d="${pathD}" fill="${glyphColor}"/>
    </g>
  </g>
</svg>`;
}

export function peerBadgeStyle({
    face,
    glyph,
    iconColor,
    bgColor,
    pathD,
    iconPath,
    label = "",
    showLabel = false,
    isStale = false,
    isTracking = false,
    scale = BADGE_SCALE_NORMAL,
}: PeerBadgeStyleOptions = {}): Style {
    const resolvedFace = face || bgColor || DEFAULT_PEER_FACE;
    const preferredGlyph = glyph || iconColor || DEFAULT_PEER_GLYPH;
    const resolvedGlyph = isStale ? STALE_GLYPH : contrastGlyphColor(resolvedFace, preferredGlyph);
    const d = pathD || iconPath || DEFAULT_MAP_PIN_PATH;

    const svg = buildPeerBadgeSvg({
        face: resolvedFace,
        glyph: resolvedGlyph,
        pathD: d,
        stale: isStale,
        tracking: isTracking,
    });
    const src = encodeSvgDataUrl(svg);
    const renderSize = isTracking && !isStale ? 48 : 40;
    const displayHeight = renderSize * scale;
    const labelOffset = -(displayHeight / 2 + 8);

    let text: Text | undefined;
    if (showLabel && label) {
        text = new Text({
            text: String(label),
            offsetY: labelOffset,
            font: "bold 12px sans-serif",
            fill: new Fill({ color: isStale ? "#6b7280" : "#111827" }),
            stroke: new Stroke({ color: "#ffffff", width: 3 }),
        });
    }

    const iconOptions = {
        src,
        anchor: [0.5, 0.5],
        scale,
        imgSize: [renderSize, renderSize],
    } as ConstructorParameters<typeof Icon>[0];

    return new Style({
        image: new Icon(iconOptions),
        text,
    });
}

export function clusterBand(count: number): ClusterBand {
    const n = Number.isFinite(count) ? Math.max(0, Math.floor(count)) : 0;
    if (n < 10) {
        return { bandId: "s", radius: 16, face: "#2563eb" };
    }
    if (n < 50) {
        return { bandId: "m", radius: 20, face: "#7c3aed" };
    }
    return { bandId: "l", radius: 24, face: "#c2410c" };
}

export function clusterBadgeStyle({ count = 0, hovered = false }: ClusterStyleOptions = {}): Style[] {
    const band = clusterBand(count);
    const radius = hovered ? band.radius + 2 : band.radius;
    const label = String(count);

    return [
        new Style({
            image: new CircleStyle({
                radius: radius + 2.5,
                fill: new Fill({ color: "rgba(15, 23, 42, 0.32)" }),
                stroke: new Stroke({ color: "rgba(15, 23, 42, 0.55)", width: 2 }),
            }),
            zIndex: 0,
        }),
        new Style({
            image: new CircleStyle({
                radius,
                fill: new Fill({ color: band.face }),
                stroke: new Stroke({ color: "#ffffff", width: 2.5 }),
            }),
            text: new Text({
                text: label,
                font: "bold 13px sans-serif",
                fill: new Fill({ color: "#ffffff" }),
                stroke: new Stroke({ color: "rgba(15,23,42,0.45)", width: 2 }),
            }),
            zIndex: 1,
        }),
    ];
}

export function getCachedClusterStyle(
    cache: Record<string, Style[]>,
    { count = 0, hovered = false }: ClusterStyleOptions = {}
): Style[] {
    const band = clusterBand(count);
    const key = `cluster-v2-${band.bandId}-${count}-${hovered ? "h" : "n"}`;
    if (cache[key]) return cache[key];
    const style = clusterBadgeStyle({ count, hovered });
    cache[key] = style;
    return style;
}

export function getCachedPeerBadgeStyle(cache: Record<string, Style>, opts: PeerBadgeStyleOptions = {}): Style {
    const {
        face,
        glyph,
        iconColor,
        bgColor,
        pathD,
        iconPath,
        label = "",
        showLabel = false,
        isStale = false,
        isTracking = false,
        scale = BADGE_SCALE_NORMAL,
    } = opts;
    const resolvedFace = face || bgColor || DEFAULT_PEER_FACE;
    const preferredGlyph = glyph || iconColor || DEFAULT_PEER_GLYPH;
    const resolvedGlyph = isStale ? STALE_GLYPH : contrastGlyphColor(resolvedFace, preferredGlyph);
    const d = pathD || iconPath || DEFAULT_MAP_PIN_PATH;
    const labelKey = showLabel && label ? String(label) : "";
    const key = [
        "peer-v2",
        resolvedFace,
        resolvedGlyph,
        d,
        labelKey,
        showLabel ? "1" : "0",
        isStale ? "1" : "0",
        isTracking ? "1" : "0",
        scale,
    ].join("|");
    if (cache[key]) return cache[key];
    const style = peerBadgeStyle({
        face: resolvedFace,
        glyph: resolvedGlyph,
        pathD: d,
        label,
        showLabel,
        isStale,
        isTracking,
        scale,
    });
    cache[key] = style;
    return style;
}

export function getPeerMarkerStyle(item: any, showLabel = false): Style {
    return peerBadgeStyle({
        face: item?.custom_background_colour || item?.background_colour || DEFAULT_PEER_FACE,
        glyph: item?.custom_foreground_colour || item?.foreground_colour || DEFAULT_PEER_GLYPH,
        label: item?.custom_display_name || item?.display_name || "",
        showLabel,
        isStale: item?.is_stale,
    });
}
