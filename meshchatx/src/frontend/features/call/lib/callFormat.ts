// SPDX-License-Identifier: 0BSD

import { HASH_BYTES_PER_SIDE } from "./constants.js";

/**
 * Formats a destination hash hex string as <12345678...12345678>
 */
export function formatDestinationHash(destinationHashHex: string | null | undefined): string {
    if (destinationHashHex == null || destinationHashHex === "") {
        return "<>";
    }
    const hex = String(destinationHashHex).trim();
    if (!hex) {
        return "<>";
    }
    const sideChars = HASH_BYTES_PER_SIDE * 2;
    if (hex.length <= sideChars * 2) {
        return `<${hex}>`;
    }
    const leftSide = hex.substring(0, sideChars);
    const rightSide = hex.substring(Math.max(0, hex.length - sideChars));
    return `<${leftSide}...${rightSide}>`;
}

/**
 * Formats raw byte count into human readable units
 */
export function formatBytes(bytes: number | null | undefined): string {
    const value = Number(bytes);
    if (!Number.isFinite(value) || value <= 0) {
        return "0 Bytes";
    }
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"];
    const i = Math.floor(Math.log(value) / Math.log(k));
    const clampedIndex = Math.min(i, sizes.length - 1);
    const formatted = parseFloat((value / Math.pow(k, clampedIndex)).toFixed(0));
    return `${formatted} ${sizes[clampedIndex]}`;
}

/**
 * Formats numeric value with locale separators
 */
export function formatNumber(value: number | string | null | undefined): string {
    if (value === 0 || value === "0") {
        return "0";
    }
    if (value == null || value === "") {
        return "0";
    }
    const n = Number(value);
    if (!Number.isFinite(n)) {
        return "0";
    }
    return n.toLocaleString();
}

/**
 * Formats bitrate in bps to bps, kbps, or Mbps
 */
export function formatBitrate(bps: number | string | null | undefined): string {
    const rate = Number(bps);
    if (!Number.isFinite(rate) || rate <= 0) {
        return "0 bps";
    }
    if (rate < 1000) {
        return `${Math.round(rate)} bps`;
    }
    if (rate < 1000000) {
        return `${(rate / 1000).toFixed(1)} kbps`;
    }
    return `${(rate / 1000000).toFixed(2)} Mbps`;
}

/**
 * Parses seconds into day, hour, minute, and second segments
 */
export function parseSeconds(secondsToFormat: number | string | null | undefined): {
    days: number;
    hours: number;
    minutes: number;
    seconds: number;
} {
    const total = Math.max(0, Math.floor(Number(secondsToFormat) || 0));
    const days = Math.floor(total / (3600 * 24));
    const hours = Math.floor((total % (3600 * 24)) / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const seconds = Math.floor(total % 60);
    return { days, hours, minutes, seconds };
}

/**
 * Formats seconds into MM:SS or HH:MM:SS format
 */
export function formatMinutesSeconds(secondsToFormat: number | string | null | undefined): string {
    const { hours, minutes, seconds } = parseSeconds(secondsToFormat);
    const formattedMinutes = minutes.toString().padStart(2, "0");
    const formattedSeconds = seconds.toString().padStart(2, "0");
    if (hours > 0) {
        return `${hours}:${formattedMinutes}:${formattedSeconds}`;
    }
    return `${formattedMinutes}:${formattedSeconds}`;
}

/**
 * Formats duration in seconds for display
 */
export function formatDuration(seconds: number | null | undefined): string {
    return formatMinutesSeconds(seconds);
}

/**
 * Formats relative time elapsed in a human friendly phrase
 */
export function formatSecondsWithoutAgo(seconds: number): string {
    const parsed = parseSeconds(seconds);
    if (parsed.days > 0) {
        return parsed.days === 1 ? "1 day" : `${parsed.days} days`;
    }
    if (parsed.hours > 0) {
        return parsed.hours === 1 ? "1 hour" : `${parsed.hours} hours`;
    }
    if (parsed.minutes > 0) {
        return parsed.minutes === 1 ? "1 minute" : `${parsed.minutes} minutes`;
    }
    if (parsed.seconds <= 1) {
        return "a second";
    }
    return `${parsed.seconds} seconds`;
}

/**
 * Formats a datetime string into relative time ago
 */
export function formatTimeAgo(datetimeString?: string | number | null): string {
    if (datetimeString == null || datetimeString === "") {
        return "unknown";
    }
    if (typeof datetimeString === "number") {
        const ms = datetimeString > 1e11 ? datetimeString : datetimeString * 1000;
        const now = Date.now();
        const diffSec = Math.round((now - ms) / 1000);
        if (diffSec < 60) {
            return "just now";
        }
        const date = new Date(ms);
        if (diffSec > 86400) {
            const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
            const month = monthNames[date.getMonth()] || "";
            const day = date.getDate();
            let hours = date.getHours();
            const minutes = date.getMinutes().toString().padStart(2, "0");
            const ampm = hours >= 12 ? "PM" : "AM";
            hours = hours % 12;
            hours = hours ? hours : 12;
            return `${month} ${day}, ${hours}:${minutes} ${ampm}`;
        }
        return `${formatSecondsWithoutAgo(diffSec)} ago`;
    }
    let dateString = String(datetimeString).trim();
    if (!dateString.includes("Z") && !dateString.includes("+")) {
        dateString = dateString.replace(" ", "T") + "Z";
    }
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) {
        return "unknown";
    }
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSec = Math.round(diffMs / 1000);

    if (diffSec < 60) {
        return "just now";
    }
    if (diffSec > 86400) {
        const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        const month = monthNames[date.getMonth()] || "";
        const day = date.getDate();
        let hours = date.getHours();
        const minutes = date.getMinutes().toString().padStart(2, "0");
        const ampm = hours >= 12 ? "PM" : "AM";
        hours = hours % 12;
        hours = hours ? hours : 12;
        return `${month} ${day}, ${hours}:${minutes} ${ampm}`;
    }
    return `${formatSecondsWithoutAgo(diffSec)} ago`;
}

/**
 * Formats unix timestamp in milliseconds or ISO date string into local date time string
 */
export function formatDateTime(timestamp: number | string | null | undefined): string {
    if (timestamp == null || timestamp === "") {
        return "";
    }
    const date = typeof timestamp === "number" ? new Date(timestamp) : new Date(String(timestamp));
    if (Number.isNaN(date.getTime())) {
        return String(timestamp);
    }
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, "0");
    const day = date.getDate().toString().padStart(2, "0");
    const hours = date.getHours().toString().padStart(2, "0");
    const minutes = date.getMinutes().toString().padStart(2, "0");
    const seconds = date.getSeconds().toString().padStart(2, "0");
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

/**
 * Computes elapsed time string for an active call given its start unix timestamp in seconds
 */
export function formatCallElapsedTime(
    callStartTimeSeconds: number | null | undefined,
    nowSeconds: number = Date.now() / 1000
): string | null {
    if (!callStartTimeSeconds || callStartTimeSeconds <= 0) {
        return null;
    }
    const elapsed = Math.max(0, Math.floor(nowSeconds - callStartTimeSeconds));
    return formatMinutesSeconds(elapsed);
}

/**
 * Computes duration string for an ended call given its start timestamp
 */
export function formatCallDuration(
    callStartTimeSeconds: number | null | undefined,
    isEnded: boolean,
    nowSeconds: number = Date.now() / 1000
): string | null {
    if (!isEnded || !callStartTimeSeconds || callStartTimeSeconds <= 0) {
        return null;
    }
    const duration = Math.max(0, Math.floor(nowSeconds - callStartTimeSeconds));
    return formatMinutesSeconds(duration);
}
