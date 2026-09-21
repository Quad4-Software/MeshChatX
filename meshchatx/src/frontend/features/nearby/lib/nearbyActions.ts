// SPDX-License-Identifier: 0BSD

/**
 * Nearby (local-link) page state and actions: WiFi hotspot hosting, WiFi
 * Direct groups, WiFi Aware sessions, NFC share/read, and QR-driven joins.
 * State is a plain object so the Svelte page can wrap it in $state and tests
 * can drive the actions without a DOM.
 */

import QRCode from "qrcode";
import ToastUtils from "../../../js/ToastUtils.js";
import { t } from "../../../js/i18n.js";
import { apiPath } from "../../../js/constants.js";
import AndroidBridge from "../../../js/rnode/AndroidBridge.js";
import { buildWifiQrPayload, parseWifiQrPayload } from "../../../js/locallinkUri.js";

export interface NearbyCapabilities {
    supported?: boolean;
    hotspot?: boolean;
    wifi_join_specifier?: boolean;
    wifi_aware?: boolean;
    wifi_aware_available?: boolean;
    wifi_direct?: boolean;
    nfc?: boolean;
    permission_nearby_wifi?: boolean;
    hotspot_active?: boolean;
    join_network_connected?: boolean;
    join_status?: string;
    satellite?: { feature?: boolean; enabled?: unknown } | null;
    [key: string]: unknown;
}

export interface WifiCredentials {
    ssid: string;
    passphrase?: string | null;
    security?: string;
    hidden?: boolean;
}

export interface AwareStatus {
    role: string;
    session: boolean;
    peers: number;
    links: number;
}

export interface NearbyState {
    loading: boolean;
    capabilities: NearbyCapabilities | null;
    nearbyWifiGranted: boolean;
    requestingPermission: boolean;
    hotspotActive: boolean;
    hotspotSsid: string | null;
    hotspotPassphrase: string | null;
    startingHotspot: boolean;
    wifiQrDataUrl: string | null;
    joinSsid: string;
    joinPassphrase: string;
    joinStatus: string;
    joining: boolean;
    pendingJoin: WifiCredentials | null;
    isScannerDialogOpen: boolean;
    scannerError: string | null;
    autoInterfaceHint: boolean;
    p2pActive: boolean;
    p2pSsid: string | null;
    p2pPassphrase: string | null;
    startingP2p: boolean;
    p2pQrDataUrl: string | null;
    awareMode: "subscribe" | "publish";
    awareStatus: AwareStatus;
    startingAware: boolean;
    nfcSharing: boolean;
    nfcReading: boolean;
    nfcLastPayload: string | null;
}

/** Poll interval handles live outside the reactive state object. */
export interface NearbyTimers {
    joinPoll: ReturnType<typeof setInterval> | null;
    awarePoll: ReturnType<typeof setInterval> | null;
    nfcPoll: ReturnType<typeof setInterval> | null;
}

export function createNearbyState(): NearbyState {
    return {
        loading: false,
        capabilities: null,
        nearbyWifiGranted: true,
        requestingPermission: false,
        hotspotActive: false,
        hotspotSsid: null,
        hotspotPassphrase: null,
        startingHotspot: false,
        wifiQrDataUrl: null,
        joinSsid: "",
        joinPassphrase: "",
        joinStatus: "idle",
        joining: false,
        pendingJoin: null,
        isScannerDialogOpen: false,
        scannerError: null,
        autoInterfaceHint: false,
        p2pActive: false,
        p2pSsid: null,
        p2pPassphrase: null,
        startingP2p: false,
        p2pQrDataUrl: null,
        awareMode: "subscribe",
        awareStatus: { role: "off", session: false, peers: 0, links: 0 },
        startingAware: false,
        nfcSharing: false,
        nfcReading: false,
        nfcLastPayload: null,
    };
}

export function createNearbyTimers(): NearbyTimers {
    return { joinPoll: null, awarePoll: null, nfcPoll: null };
}

// Derived flags
// ------------------------------------------------------------------
export function capabilityBadges(state: NearbyState): { key: string; label: string; ok: boolean }[] {
    const caps = state.capabilities || {};
    const label = (key: string) => t(`tools.nearby.cap_${key}`);
    return [
        { key: "hotspot", label: label("hotspot"), ok: Boolean(caps.hotspot) },
        { key: "join", label: label("join"), ok: Boolean(caps.wifi_join_specifier) },
        { key: "aware", label: label("aware"), ok: Boolean(caps.wifi_aware_available) },
        { key: "direct", label: label("direct"), ok: Boolean(caps.wifi_direct) },
        { key: "nfc", label: label("nfc"), ok: Boolean(caps.nfc) },
        { key: "satellite", label: label("satellite"), ok: Boolean(caps.satellite?.feature) },
    ];
}

export function satelliteEnabled(state: NearbyState): boolean {
    return Boolean(state.capabilities?.satellite?.enabled);
}

export function canUseHotspot(state: NearbyState): boolean {
    return Boolean(state.capabilities?.supported && state.capabilities?.hotspot);
}

export function canUseP2p(state: NearbyState): boolean {
    return Boolean(state.capabilities?.supported && state.capabilities?.wifi_direct);
}

export function canUseAware(state: NearbyState): boolean {
    return Boolean(state.capabilities?.supported && state.capabilities?.wifi_aware_available);
}

export function canUseNfc(state: NearbyState): boolean {
    return Boolean(state.capabilities?.supported && state.capabilities?.nfc);
}

export function awareActive(state: NearbyState): boolean {
    return state.awareStatus.role !== "off" || state.awareStatus.session;
}

export function nfcSharePayload(state: NearbyState): string | null {
    if (state.hotspotActive && state.hotspotSsid && state.hotspotPassphrase) {
        return buildWifiQrPayload({
            ssid: state.hotspotSsid,
            passphrase: state.hotspotPassphrase,
        });
    }
    if (state.p2pActive && state.p2pSsid && state.p2pPassphrase) {
        return buildWifiQrPayload({
            ssid: state.p2pSsid,
            passphrase: state.p2pPassphrase,
        });
    }
    return null;
}

export function nfcPayloadJoinable(state: NearbyState): boolean {
    return Boolean(state.nfcLastPayload && parseWifiQrPayload(state.nfcLastPayload));
}

export function joinConnected(state: NearbyState): boolean {
    return Boolean(state.capabilities?.join_network_connected);
}

// Loads
// ------------------------------------------------------------------
export async function refreshAll(state: NearbyState, bridge: AndroidBridge): Promise<void> {
    state.loading = true;
    try {
        await Promise.all([loadCapabilities(state, bridge), loadInterfaces(state)]);
    } finally {
        state.loading = false;
    }
}

export async function loadCapabilities(state: NearbyState, bridge: AndroidBridge): Promise<void> {
    try {
        const res = await window.api.get(apiPath("/locallink/capabilities"));
        const caps: NearbyCapabilities = res.data || {};
        state.capabilities = caps;
        if (caps.supported) {
            state.nearbyWifiGranted =
                Boolean(caps.permission_nearby_wifi) || bridge.hasPermission(AndroidBridge.PERM_NEARBY_WIFI);
        }
        if (caps.hotspot_active && !state.hotspotActive) {
            await loadHotspotStatus(state);
        }
    } catch {
        state.capabilities = { supported: false };
    }
}

export async function loadHotspotStatus(state: NearbyState): Promise<void> {
    try {
        const res = await window.api.get(apiPath("/locallink/hotspot/status"));
        state.hotspotActive = Boolean(res.data?.active);
        if (state.hotspotActive && !state.hotspotSsid) {
            state.hotspotSsid = res.data?.ssid || null;
        }
    } catch {
        // status is best effort
    }
}

export async function loadInterfaces(state: NearbyState): Promise<void> {
    try {
        const res = await window.api.get(apiPath("/reticulum/interfaces"));
        const interfaces = res.data?.interfaces || {};
        const hasAuto = Object.values(interfaces).some(
            (iface: any) => iface && iface.type === "AutoInterface" && iface.enabled
        );
        state.autoInterfaceHint = !hasAuto;
    } catch {
        state.autoInterfaceHint = false;
    }
}

export async function requestNearbyPermission(state: NearbyState, bridge: AndroidBridge): Promise<void> {
    state.requestingPermission = true;
    try {
        const result = await bridge.requestPermission(AndroidBridge.PERM_NEARBY_WIFI);
        if (result === "granted") {
            state.nearbyWifiGranted = true;
            await loadCapabilities(state, bridge);
        } else if (result === "settings") {
            ToastUtils.warning(t("tools.nearby.permission_settings"));
        }
    } finally {
        state.requestingPermission = false;
    }
}

// Hotspot
// ------------------------------------------------------------------
export async function startHotspot(state: NearbyState): Promise<void> {
    state.startingHotspot = true;
    try {
        const res = await window.api.post(apiPath("/locallink/hotspot/start"), {});
        const data = res.data || {};
        if (!data.ok) {
            ToastUtils.error(data.error || t("tools.nearby.hotspot_failed"));
            return;
        }
        state.hotspotActive = true;
        state.hotspotSsid = data.ssid;
        state.hotspotPassphrase = data.passphrase;
        await renderWifiQr(state);
        ToastUtils.success(t("tools.nearby.hotspot_started"));
    } catch (e: any) {
        ToastUtils.error(e?.response?.data?.error || t("tools.nearby.hotspot_failed"));
    } finally {
        state.startingHotspot = false;
    }
}

export async function stopHotspot(state: NearbyState): Promise<void> {
    try {
        await window.api.post(apiPath("/locallink/hotspot/stop"), {});
        state.hotspotActive = false;
        state.hotspotSsid = null;
        state.hotspotPassphrase = null;
        state.wifiQrDataUrl = null;
        ToastUtils.info(t("tools.nearby.hotspot_stopped"));
    } catch (e: any) {
        ToastUtils.error(e?.response?.data?.error || t("tools.nearby.hotspot_failed"));
    }
}

export async function rotateHotspot(state: NearbyState): Promise<void> {
    await stopHotspot(state);
    await startHotspot(state);
}

export async function renderWifiQr(state: NearbyState): Promise<void> {
    const payload = buildWifiQrPayload({
        ssid: state.hotspotSsid ?? "",
        passphrase: state.hotspotPassphrase ?? "",
    });
    state.wifiQrDataUrl = payload ? await QRCode.toDataURL(payload, { margin: 1, scale: 6 }) : null;
}

export async function copyValue(value: string | null): Promise<void> {
    if (!value) return;
    try {
        await navigator.clipboard.writeText(value);
        ToastUtils.success(t("common.copied"));
    } catch {
        ToastUtils.error(t("common.failed_to_copy"));
    }
}

// QR scan -> join flow
// ------------------------------------------------------------------
/**
 * Handle a decoded QR payload. Returns true when a wifi payload was accepted
 * and the caller should close the scanner; otherwise records the error on
 * state so the scan loop can keep going.
 */
export function toWifiCredentials(parsed: ReturnType<typeof parseWifiQrPayload>): WifiCredentials | null {
    if (!parsed || !parsed.ssid) return null;
    return {
        ssid: parsed.ssid,
        passphrase: parsed.passphrase,
        security: parsed.security,
        hidden: parsed.hidden,
    };
}

export function onQrScanned(state: NearbyState, raw: string): boolean {
    const creds = toWifiCredentials(parseWifiQrPayload(raw));
    if (!creds) {
        state.scannerError = t("tools.nearby.qr_not_wifi");
        return false;
    }
    state.pendingJoin = creds;
    return true;
}

export async function confirmJoin(state: NearbyState, timers?: NearbyTimers, bridge?: AndroidBridge): Promise<void> {
    if (!state.pendingJoin) return;
    const { ssid, passphrase } = state.pendingJoin;
    state.pendingJoin = null;
    await joinNetwork(state, ssid, passphrase ?? null, timers, bridge);
}

export async function joinManual(state: NearbyState, timers?: NearbyTimers, bridge?: AndroidBridge): Promise<void> {
    if (!state.joinSsid) return;
    await joinNetwork(state, state.joinSsid.trim(), state.joinPassphrase || null, timers, bridge);
}

export async function joinNetwork(
    state: NearbyState,
    ssid: string,
    passphrase: string | null,
    timers?: NearbyTimers,
    bridge?: AndroidBridge
): Promise<void> {
    state.joining = true;
    try {
        const res = await window.api.post(apiPath("/locallink/wifi/join"), {
            ssid,
            passphrase,
        });
        const data = res.data || {};
        if (!data.ok && data.status !== "requested") {
            ToastUtils.error(data.error || t("tools.nearby.join_failed"));
            return;
        }
        state.joinStatus = data.status || "requested";
        ToastUtils.info(t("tools.nearby.join_requested"));
        const activeBridge = bridge ?? new AndroidBridge();
        if (timers) {
            startJoinPolling(state, timers, activeBridge);
        }
        await loadCapabilities(state, activeBridge);
    } catch (e: any) {
        ToastUtils.error(e?.response?.data?.error || t("tools.nearby.join_failed"));
    } finally {
        state.joining = false;
    }
}

export function startJoinPolling(state: NearbyState, timers: NearbyTimers, bridge: AndroidBridge): void {
    stopJoinPolling(timers);
    let attempts = 0;
    timers.joinPoll = setInterval(async () => {
        attempts += 1;
        await loadCapabilities(state, bridge);
        if (joinConnected(state) || attempts >= 10 || state.capabilities?.join_status === "idle") {
            stopJoinPolling(timers);
        }
    }, 3000);
}

export function stopJoinPolling(timers: NearbyTimers): void {
    if (timers.joinPoll) {
        clearInterval(timers.joinPoll);
        timers.joinPoll = null;
    }
}

export async function leaveNetwork(state: NearbyState, timers: NearbyTimers, bridge: AndroidBridge): Promise<void> {
    try {
        await window.api.post(apiPath("/locallink/wifi/leave"), {});
        state.joinStatus = "idle";
        stopJoinPolling(timers);
        await loadCapabilities(state, bridge);
        ToastUtils.info(t("tools.nearby.left"));
    } catch (e: any) {
        ToastUtils.error(e?.response?.data?.error || t("tools.nearby.join_failed"));
    }
}
