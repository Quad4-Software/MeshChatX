import dayjs from "dayjs";

class Utils {
    static formatDestinationHash(destinationHashHex) {
        const bytesPerSide = 4;
        const leftSide = destinationHashHex.substring(0, bytesPerSide * 2);
        const rightSide = destinationHashHex.substring(destinationHashHex.length - bytesPerSide * 2);
        return `<${leftSide}...${rightSide}>`;
    }

    static formatBytes(bytes) {
        if (!bytes || bytes <= 0) {
            return "0 Bytes";
        }

        const k = 1024;
        const decimals = 0;
        const sizes = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"];

        const i = Math.floor(Math.log(bytes) / Math.log(k));

        return parseFloat((bytes / Math.pow(k, i)).toFixed(decimals)) + " " + sizes[i];
    }

    static formatNumber(num) {
        if (num === 0) {
            return "0";
        }
        if (num === null || num === undefined) {
            return "0";
        }
        return num.toLocaleString();
    }

    static parseSeconds(secondsToFormat) {
        secondsToFormat = Number(secondsToFormat);
        var days = Math.floor(secondsToFormat / (3600 * 24));
        var hours = Math.floor((secondsToFormat % (3600 * 24)) / 3600);
        var minutes = Math.floor((secondsToFormat % 3600) / 60);
        var seconds = Math.floor(secondsToFormat % 60);
        return {
            days: days,
            hours: hours,
            minutes: minutes,
            seconds: seconds,
        };
    }

    static formatSecondsWithoutAgo(seconds) {
        const parsedSeconds = this.parseSeconds(seconds);

        if (parsedSeconds.days > 0) {
            return parsedSeconds.days === 1 ? "1 day" : parsedSeconds.days + " days";
        }

        if (parsedSeconds.hours > 0) {
            return parsedSeconds.hours === 1 ? "1 hour" : parsedSeconds.hours + " hours";
        }

        if (parsedSeconds.minutes > 0) {
            return parsedSeconds.minutes === 1 ? "1 minute" : parsedSeconds.minutes + " minutes";
        }

        if (parsedSeconds.seconds <= 1) {
            return "a second";
        }

        return parsedSeconds.seconds + " seconds";
    }

    static formatSeconds(seconds) {
        return this.formatSecondsWithoutAgo(seconds) + " ago";
    }

    static formatTimeAgo(datetimeString) {
        if (!datetimeString) return "unknown";

        // ensure UTC if no timezone is provided
        let dateString = datetimeString;
        if (typeof dateString === "string" && !dateString.includes("Z") && !dateString.includes("+")) {
            // SQLite CURRENT_TIMESTAMP format is YYYY-MM-DD HH:MM:SS
            // Replace space with T and append Z for ISO format
            dateString = dateString.replace(" ", "T") + "Z";
        }

        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffSec = Math.round(diffMs / 1000);

        if (diffSec < 60) {
            return "just now";
        }

        // If older than 24 hours, show full date
        if (diffSec > 86400) {
            return dayjs(date).format("MMM D, h:mm A");
        }

        return this.formatSeconds(diffSec);
    }

    /**
     * Relative age fragment without trailing " ago" / "ago" duplication when used inside i18n
     * strings that already add a locale-specific suffix (e.g. "Last synced {time} ago.").
     * Sub-minute uses a neutral phrase so English templates avoid "just now ago".
     */
    static formatTimeAgoForI18n(datetimeString) {
        if (!datetimeString) return "unknown";

        let dateString = datetimeString;
        if (typeof dateString === "string" && !dateString.includes("Z") && !dateString.includes("+")) {
            dateString = dateString.replace(" ", "T") + "Z";
        }

        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffSec = Math.round(diffMs / 1000);

        if (diffSec < 60) {
            return "less than a minute";
        }

        if (diffSec > 86400) {
            return dayjs(date).format("MMM D, h:mm A");
        }

        return this.formatSecondsWithoutAgo(diffSec);
    }

    static formatSecondsAgo(seconds) {
        const secondsAgo = Math.round(Date.now() / 1000 - seconds);
        return this.formatSeconds(secondsAgo);
    }

    static formatSecondsAgoForI18n(seconds) {
        const secondsAgo = Math.round(Date.now() / 1000 - seconds);
        if (secondsAgo < 60) {
            return "less than a minute";
        }
        return this.formatSecondsWithoutAgo(secondsAgo);
    }

    static formatMinutesSeconds(seconds) {
        const parsedSeconds = this.parseSeconds(seconds);
        const paddedMinutes = parsedSeconds.minutes.toString().padStart(2, "0");
        const paddedSeconds = parsedSeconds.seconds.toString().padStart(2, "0");
        return `${paddedMinutes}:${paddedSeconds}`;
    }

    static convertUnixMillisToLocalDateTimeString(unixTimestampInMilliseconds) {
        return dayjs(unixTimestampInMilliseconds).format("YYYY-MM-DD hh:mm A");
    }

    static convertDateTimeToLocalDateTimeString(dateTime) {
        return this.convertUnixMillisToLocalDateTimeString(dateTime.getTime());
    }

    static arrayBufferToBase64(arrayBuffer) {
        var binary = "";
        var bytes = new Uint8Array(arrayBuffer);
        var len = bytes.byteLength;
        for (var i = 0; i < len; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return window.btoa(binary);
    }

    static formatBitsPerSecond(bits) {
        if (!bits || bits <= 0) {
            return "0 bps";
        }

        const k = 1000; // Use 1000 instead of 1024 for network speeds
        const decimals = 0;
        const sizes = ["bps", "kbps", "Mbps", "Gbps", "Tbps", "Pbps", "Ebps", "Zbps", "Ybps"];

        const i = Math.max(0, Math.floor(Math.log(bits) / Math.log(k)));

        return parseFloat((bits / Math.pow(k, i)).toFixed(decimals)) + " " + sizes[i];
    }

    static formatBytesPerSecond(bytesPerSecond) {
        if (!bytesPerSecond || bytesPerSecond <= 0) {
            return "0 B/s";
        }

        const k = 1024;
        const decimals = 1;
        const sizes = ["B/s", "KB/s", "MB/s", "GB/s", "TB/s", "PB/s", "EB/s", "ZB/s", "YB/s"];

        const i = Math.max(0, Math.floor(Math.log(bytesPerSecond) / Math.log(k)));

        return parseFloat((bytesPerSecond / Math.pow(k, i)).toFixed(decimals)) + " " + sizes[i];
    }

    static formatCountupDuration(totalSeconds) {
        const seconds = Math.max(0, Math.floor(Number(totalSeconds) || 0));
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const remainingSeconds = seconds % 60;
        if (hours > 0) {
            return `${hours}:${String(minutes).padStart(2, "0")}:${String(remainingSeconds).padStart(2, "0")}`;
        }
        return `${minutes}:${String(remainingSeconds).padStart(2, "0")}`;
    }

    static lxmfMessageTransferTotalBytes(lxmfMessage, base64ByteLength = null) {
        if (!lxmfMessage) {
            return 0;
        }

        const decodeBase64Length = (value) => {
            if (!value || typeof base64ByteLength !== "function") {
                return 0;
            }
            return base64ByteLength(value);
        };

        let total = 0;
        const content = lxmfMessage.content || "";
        if (content) {
            total += new TextEncoder().encode(content).length;
        }

        const fields = lxmfMessage.fields || {};
        const image = fields.image;
        if (image) {
            if (image.image_size != null) {
                total += Number(image.image_size) || 0;
            } else if (image.image_bytes) {
                total += decodeBase64Length(image.image_bytes);
            }
        }

        const audio = fields.audio;
        if (audio) {
            if (audio.audio_size != null) {
                total += Number(audio.audio_size) || 0;
            } else if (audio.audio_bytes) {
                total += decodeBase64Length(audio.audio_bytes);
            }
        }

        const fileAttachments = fields.file_attachments;
        if (Array.isArray(fileAttachments)) {
            for (const file of fileAttachments) {
                if (file?.file_size != null) {
                    total += Number(file.file_size) || 0;
                } else if (file?.file_bytes) {
                    total += decodeBase64Length(file.file_bytes);
                }
            }
        }

        return total;
    }

    static formatFrequency(hz) {
        const n = Number(hz);
        if (!Number.isFinite(n) || n <= 0) {
            return "0 Hz";
        }

        const k = 1000;
        const rounded = Math.round(n);
        const sizes = ["Hz", "kHz", "MHz", "GHz", "THz", "PHz", "EHz", "ZHz", "YHz"];
        const i = Math.floor(Math.log(rounded) / Math.log(k));

        return parseFloat((rounded / Math.pow(k, i)).toFixed(6)) + " " + sizes[i];
    }

    static decodeBase64ToUtf8String(base64) {
        // support for decoding base64 as a utf8 string to support emojis and cyrillic characters etc
        return decodeURIComponent(
            atob(base64)
                .split("")
                .map(function (c) {
                    return "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2);
                })
                .join("")
        );
    }

    static isInterfaceEnabled(iface) {
        const rawValue = iface.enabled ?? iface.interface_enabled;
        const value = rawValue?.toString()?.toLowerCase();
        return value === "on" || value === "yes" || value === "true";
    }

    static escapeHtml(text) {
        if (text == null) return "";
        text = String(text);
        const map = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;",
        };
        return text.replace(/[&<>"']/g, function (m) {
            return map[m];
        });
    }

    /**
     * Return lowercase hex digits only (strips UUID hyphens, colons, whitespace).
     */
    static normalizeMeshchatHashHex(value) {
        if (!value || typeof value !== "string") {
            return "";
        }
        let h = value.trim().toLowerCase();
        if (h.includes("://")) {
            h = h.split("://")[1];
        }
        if (h.includes("@")) {
            h = h.split("@")[1];
        }
        if (h.includes(":")) {
            h = h.split(":")[0];
        }
        return h.replace(/[^0-9a-f]/g, "");
    }
}

export default Utils;
