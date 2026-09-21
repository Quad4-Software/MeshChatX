// SPDX-License-Identifier: 0BSD

/**
 * Nearby transports that do not ride the hosted/joined wifi network: WiFi
 * Direct groups, WiFi Aware sessions, and NFC credential share/read.
 */

import QRCode from "qrcode";
import ToastUtils from "../../../js/ToastUtils.js";
import { t } from "../../../js/i18n.js";
import { apiPath } from "../../../js/constants.js";
import { buildWifiQrPayload, parseWifiQrPayload } from "../../../js/locallinkUri.js";
import { nfcSharePayload, toWifiCredentials } from "./nearbyActions.js";
import type { NearbyState, NearbyTimers } from "./nearbyActions.js";

// WiFi Direct
// ------------------------------------------------------------------
export async function loadP2pStatus(state: NearbyState): Promise<void> {
    try {
        const res = await window.api.get(apiPath("/locallink/p2p/status"));
        state.p2pActive = Boolean(res.data?.active);
        if (state.p2pActive && !state.p2pSsid) {
            state.p2pSsid = res.data?.ssid || null;
        }
    } catch {
        state.p2pActive = false;
    }
}

export async function startP2p(state: NearbyState): Promise<void> {
    state.startingP2p = true;
    try {
        const res = await window.api.post(apiPath("/locallink/p2p/start"), {});
        const data = res.data || {};
        if (!data.ok) {
            ToastUtils.error(data.error || t("tools.nearby.group_failed"));
            return;
        }
        state.p2pActive = true;
        state.p2pSsid = data.ssid;
        state.p2pPassphrase = data.passphrase;
        const payload = buildWifiQrPayload({
            ssid: state.p2pSsid ?? "",
            passphrase: state.p2pPassphrase ?? "",
        });
        state.p2pQrDataUrl = payload ? await QRCode.toDataURL(payload, { margin: 1, scale: 6 }) : null;
        ToastUtils.success(t("tools.nearby.group_started"));
    } catch (e: any) {
        ToastUtils.error(e?.response?.data?.error || t("tools.nearby.group_failed"));
    } finally {
        state.startingP2p = false;
    }
}

export async function stopP2p(state: NearbyState): Promise<void> {
    try {
        await window.api.post(apiPath("/locallink/p2p/stop"), {});
        state.p2pActive = false;
        state.p2pSsid = null;
        state.p2pPassphrase = null;
        state.p2pQrDataUrl = null;
        ToastUtils.info(t("tools.nearby.group_stopped"));
    } catch (e: any) {
        ToastUtils.error(e?.response?.data?.error || t("tools.nearby.group_failed"));
    }
}

// WiFi Aware
// ------------------------------------------------------------------
export async function loadAwareStatus(state: NearbyState): Promise<void> {
    try {
        const res = await window.api.get(apiPath("/locallink/aware/status"));
        const data = res.data || {};
        state.awareStatus = {
            role: data.role || "off",
            session: Boolean(data.session),
            peers: data.peers || 0,
            links: data.links || 0,
        };
    } catch {
        state.awareStatus = { role: "off", session: false, peers: 0, links: 0 };
    }
}

export async function startAware(state: NearbyState, timers?: NearbyTimers): Promise<void> {
    state.startingAware = true;
    try {
        const res = await window.api.post(apiPath("/locallink/aware/start"), {
            mode: state.awareMode,
        });
        const data = res.data || {};
        if (!data.ok) {
            ToastUtils.error(data.error || t("tools.nearby.aware_failed"));
            return;
        }
        state.awareStatus.role = state.awareMode;
        state.awareStatus.session = true;
        ToastUtils.success(t("tools.nearby.aware_started"));
        if (timers) {
            startAwarePolling(state, timers);
        }
    } catch (e: any) {
        ToastUtils.error(e?.response?.data?.error || t("tools.nearby.aware_failed"));
    } finally {
        state.startingAware = false;
    }
}

export async function stopAware(state: NearbyState, timers?: NearbyTimers): Promise<void> {
    try {
        await window.api.post(apiPath("/locallink/aware/stop"), {});
        state.awareStatus = { role: "off", session: false, peers: 0, links: 0 };
        if (timers) {
            stopAwarePolling(timers);
        }
        ToastUtils.info(t("tools.nearby.aware_stopped"));
    } catch (e: any) {
        ToastUtils.error(e?.response?.data?.error || t("tools.nearby.aware_failed"));
    }
}

export function startAwarePolling(state: NearbyState, timers: NearbyTimers): void {
    stopAwarePolling(timers);
    timers.awarePoll = setInterval(() => void loadAwareStatus(state), 3000);
}

export function stopAwarePolling(timers: NearbyTimers): void {
    if (timers.awarePoll) {
        clearInterval(timers.awarePoll);
        timers.awarePoll = null;
    }
}

// NFC
// ------------------------------------------------------------------
export async function loadNfcStatus(state: NearbyState): Promise<void> {
    try {
        const res = await window.api.get(apiPath("/locallink/nfc/status"));
        const data = res.data || {};
        state.nfcSharing = Boolean(data.sharing);
        state.nfcReading = Boolean(data.reading);
        if (data.last_payload) {
            state.nfcLastPayload = data.last_payload;
        }
    } catch {
        // status is best effort
    }
}

export async function startNfcShare(state: NearbyState): Promise<void> {
    try {
        const res = await window.api.post(apiPath("/locallink/nfc/share"), {
            payload: nfcSharePayload(state),
        });
        const data = res.data || {};
        if (!data.ok) {
            ToastUtils.error(data.error || t("tools.nearby.nfc_failed"));
            return;
        }
        state.nfcSharing = true;
        ToastUtils.info(t("tools.nearby.nfc_sharing_note"));
    } catch (e: any) {
        ToastUtils.error(e?.response?.data?.error || t("tools.nearby.nfc_failed"));
    }
}

export async function stopNfcShare(state: NearbyState): Promise<void> {
    try {
        await window.api.post(apiPath("/locallink/nfc/share"), { payload: null });
        state.nfcSharing = false;
    } catch (e: any) {
        ToastUtils.error(e?.response?.data?.error || t("tools.nearby.nfc_failed"));
    }
}

export async function startNfcRead(state: NearbyState, timers?: NearbyTimers): Promise<void> {
    try {
        const res = await window.api.post(apiPath("/locallink/nfc/read/start"), {});
        const data = res.data || {};
        if (!data.ok) {
            ToastUtils.error(data.error || t("tools.nearby.nfc_failed"));
            return;
        }
        state.nfcReading = true;
        state.nfcLastPayload = null;
        if (timers) {
            startNfcPolling(state, timers);
        }
    } catch (e: any) {
        ToastUtils.error(e?.response?.data?.error || t("tools.nearby.nfc_failed"));
    }
}

export async function stopNfcRead(state: NearbyState, timers?: NearbyTimers): Promise<void> {
    try {
        await window.api.post(apiPath("/locallink/nfc/read/stop"), {});
        state.nfcReading = false;
        if (timers) {
            stopNfcPolling(timers);
        }
    } catch (e: any) {
        ToastUtils.error(e?.response?.data?.error || t("tools.nearby.nfc_failed"));
    }
}

export function startNfcPolling(state: NearbyState, timers: NearbyTimers): void {
    stopNfcPolling(timers);
    timers.nfcPoll = setInterval(() => void loadNfcStatus(state), 1500);
}

export function stopNfcPolling(timers: NearbyTimers): void {
    if (timers.nfcPoll) {
        clearInterval(timers.nfcPoll);
        timers.nfcPoll = null;
    }
}

export function joinFromNfc(state: NearbyState): void {
    const creds = toWifiCredentials(state.nfcLastPayload ? parseWifiQrPayload(state.nfcLastPayload) : null);
    if (creds) {
        state.pendingJoin = creds;
    }
}
