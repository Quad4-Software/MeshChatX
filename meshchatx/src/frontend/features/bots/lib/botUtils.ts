// SPDX-License-Identifier: 0BSD

import { isDestinationHash } from "../../../js/meshValidate.js";
import type { BotRecord } from "./types.js";

export function lxmfAddressFor(bot: BotRecord | null | undefined): string {
    if (!bot) {
        return "";
    }
    const raw = bot.lxmf_address || bot.full_address || bot.address;
    if (!raw || typeof raw !== "string") {
        return "";
    }
    const h = raw.trim().toLowerCase();
    return isDestinationHash(h) ? h : "";
}

export function botLastError(bot: BotRecord | null | undefined): string {
    const t = (bot?.last_error || "").trim();
    return t;
}

export function formatEffectiveLxmfConfig(effective: Record<string, unknown> | null | undefined): string {
    if (!effective || typeof effective !== "object") {
        return "";
    }
    return JSON.stringify(effective, null, 2);
}

export function formatRelativeSince(iso: string | null | undefined, _relativeTimerTick = 0): string {
    if (!iso) {
        return "";
    }
    let t: number;
    try {
        t = new Date(iso).getTime();
    } catch {
        return String(iso);
    }
    if (Number.isNaN(t)) {
        return String(iso);
    }
    const now = Date.now();
    let sec = Math.floor((now - t) / 1000);
    if (sec < 0) {
        sec = 0;
    }
    if (sec < 60) {
        return `${sec}s`;
    }
    const min = Math.floor(sec / 60);
    if (min < 60) {
        return `${min}m`;
    }
    const h = Math.floor(min / 60);
    if (h < 24) {
        return `${h}h`;
    }
    const d = Math.floor(h / 24);
    if (d < 30) {
        return d === 1 ? "1 day" : `${d} days`;
    }
    const mo = Math.floor(d / 30);
    if (d < 365) {
        return mo === 1 ? "1 month" : `${mo} months`;
    }
    const y = Math.floor(d / 365);
    return y === 1 ? "1 year" : `${y} years`;
}
