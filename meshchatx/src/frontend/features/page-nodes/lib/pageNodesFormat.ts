// SPDX-License-Identifier: 0BSD

import { t } from "../../../js/i18n.js";
import Utils from "../../../js/Utils.js";
import {
    ANNOUNCE_INTERVAL_MAX_MINUTES,
    ANNOUNCE_INTERVAL_MIN_MINUTES,
    DEFAULT_ANNOUNCE_INTERVAL_SECONDS,
} from "./constants.js";

/** Formats mesh uptime into human readable duration string */
export function formatMeshUptime(seconds?: number | null): string {
    if (seconds == null || seconds < 0) {
        return "-";
    }
    let s = Math.floor(seconds);
    if (s < 60) {
        return `${s}s`;
    }
    if (s < 3600) {
        return `${Math.floor(s / 60)}m`;
    }
    if (s < 86400) {
        return `${Math.floor(s / 3600)}h`;
    }
    if (s < 30 * 86400) {
        return `${Math.floor(s / 86400)}d`;
    }
    const yearSec = 365 * 86400;
    const monthSec = 30 * 86400;
    const years = Math.floor(s / yearSec);
    s -= years * yearSec;
    const months = Math.floor(s / monthSec);
    s -= months * monthSec;
    const days = Math.floor(s / 86400);
    const parts: string[] = [];
    if (years) {
        parts.push(`${years} year${years === 1 ? "" : "s"}`);
    }
    if (months) {
        parts.push(`${months} month${months === 1 ? "" : "s"}`);
    }
    if (days) {
        parts.push(`${days} day${days === 1 ? "" : "s"}`);
    }
    return parts.length ? parts.join(" ") : "0d";
}

/** Formats byte counts into human readable file size */
export function formatFileSize(bytes?: number | null): string {
    if (bytes == null || bytes < 0) {
        return "0 B";
    }
    if (bytes < 1024) {
        return `${bytes} B`;
    }
    if (bytes < 1024 * 1024) {
        return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Resolves numerical announce interval seconds with fallback */
export function resolveAnnounceIntervalSeconds(
    seconds: unknown,
    defaultSeconds: number = DEFAULT_ANNOUNCE_INTERVAL_SECONDS
): number {
    if (seconds == null) {
        return defaultSeconds;
    }
    const n = Number(seconds);
    if (!Number.isFinite(n)) {
        return defaultSeconds;
    }
    return n;
}

/** Converts seconds to rounded announce minutes */
export function secondsToAnnounceMinutes(seconds: unknown): number {
    const sec = resolveAnnounceIntervalSeconds(seconds, DEFAULT_ANNOUNCE_INTERVAL_SECONDS);
    if (sec === 0) {
        return 0;
    }
    return Math.round(sec / 60);
}

/** Converts announce minutes input into clamped seconds */
export function announceMinutesToSeconds(minutes: unknown): number {
    const n = Number(minutes);
    if (Number.isFinite(n) && n === 0) {
        return 0;
    }
    const clamped = Math.max(
        ANNOUNCE_INTERVAL_MIN_MINUTES,
        Math.min(ANNOUNCE_INTERVAL_MAX_MINUTES, Number.isFinite(n) ? n : ANNOUNCE_INTERVAL_MIN_MINUTES)
    );
    return clamped * 60;
}

/** Formats last announced timestamp using relative time translation */
export function formatLastAnnounced(lastAnnouncedAt?: number | null): string {
    if (!lastAnnouncedAt) {
        return t("tools.mesh_server.never_announced");
    }
    return t("tools.mesh_server.last_announced_ago", {
        time: Utils.formatSecondsAgoForI18n(lastAnnouncedAt),
    });
}
