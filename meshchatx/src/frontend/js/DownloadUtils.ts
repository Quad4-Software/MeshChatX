function isAndroidSaveBridge() {
    return (
        typeof window !== "undefined" &&
        window.MeshChatXAndroid != null &&
        typeof window.MeshChatXAndroid.saveDownload === "function"
    );
}

class DownloadUtils {
    static sanitizeDownloadFilename(filename, defaultFilename = "download") {
        let name = filename == null ? "" : String(filename);

        // Strip CR/LF/NUL and bidi overrides without embedding control chars in a regex literal.
        name = Array.from(name)
            .filter((ch) => {
                const c = ch.codePointAt(0) ?? 0;
                if (c === 0 || c === 10 || c === 13) return false;
                if (c >= 0x202a && c <= 0x202e) return false;
                if (c >= 0x2066 && c <= 0x2069) return false;
                return true;
            })
            .join("")
            .trim();
        // Drop path segments from naive Content-Disposition or peer-provided names.
        name = name.split(/[/\\]/).pop() || "";
        name = name.replace(/[. ]+$/g, "");
        if (!name || name === "." || name === "..") {
            return defaultFilename;
        }
        const stem = name.includes(".") ? name.slice(0, name.lastIndexOf(".")) : name;
        if (/^(con|prn|aux|nul|com[1-9]|lpt[1-9])$/i.test(stem)) {
            return defaultFilename;
        }
        return name;
    }

    static parseFilenameFromContentDisposition(header, defaultFilename) {
        if (!header || typeof header !== "string") {
            return defaultFilename;
        }
        const star = header.match(/filename\*=UTF-8''([^;\s]+)/i);
        if (star?.[1]) {
            try {
                return DownloadUtils.sanitizeDownloadFilename(decodeURIComponent(star[1]), defaultFilename);
            } catch {
                // fall through
            }
        }
        const plain = header.match(/filename="?([^";\n]+)"?/i);
        if (plain?.[1]) {
            return DownloadUtils.sanitizeDownloadFilename(plain[1].trim(), defaultFilename);
        }
        return defaultFilename;
    }

    static headerValue(headers, name) {
        if (!headers) {
            return undefined;
        }
        if (typeof headers.get === "function") {
            const fromGet = headers.get(name);
            return fromGet == null || fromGet === "" ? undefined : fromGet;
        }
        const lower = String(name).toLowerCase();
        for (const key of Object.keys(headers)) {
            if (String(key).toLowerCase() === lower) {
                return headers[key];
            }
        }
        return undefined;
    }

    static async downloadFromApiResponse(response, defaultFilename) {
        const headers = response?.headers || {};
        const cd = DownloadUtils.headerValue(headers, "content-disposition");
        const filename = DownloadUtils.parseFilenameFromContentDisposition(cd, defaultFilename);
        const type = DownloadUtils.headerValue(headers, "content-type") || "application/octet-stream";
        const blob = new Blob([response.data], { type });
        await DownloadUtils.downloadFile(filename, blob);
    }

    static _blobToBase64(blob) {
        return new Promise<any>((resolve, reject) => {
            const reader = new FileReader();
            reader.onloadend = () => {
                const s = reader.result;
                if (typeof s !== "string") {
                    reject(new Error("readAsDataURL failed"));
                    return;
                }
                const comma = s.indexOf(",");
                resolve(comma >= 0 ? s.slice(comma + 1) : s);
            };
            reader.onerror = () => reject(reader.error || new Error("read failed"));
            reader.readAsDataURL(blob);
        });
    }

    static _triggerBrowserDownload(filename, objectUrl) {
        const link = document.createElement("a");
        link.href = objectUrl;
        link.download = filename;
        link.style.display = "none";
        document.body.append(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(objectUrl), 10000);
    }

    static downloadFromBase64(filename, fileBytesBase64) {
        const safeName = DownloadUtils.sanitizeDownloadFilename(filename, "download");
        if (isAndroidSaveBridge()) {
            window.MeshChatXAndroid.saveDownload(safeName, fileBytesBase64);
            return;
        }
        const byteCharacters = atob(fileBytesBase64);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        const blob = new Blob([byteArray]);
        const objectUrl = URL.createObjectURL(blob);
        DownloadUtils._triggerBrowserDownload(safeName, objectUrl);
    }

    static async downloadFile(filename, blob) {
        const safeName = DownloadUtils.sanitizeDownloadFilename(filename, "download");
        if (isAndroidSaveBridge()) {
            const b64 = await DownloadUtils._blobToBase64(blob);
            window.MeshChatXAndroid.saveDownload(safeName, b64);
            return;
        }
        const objectUrl = URL.createObjectURL(blob);
        DownloadUtils._triggerBrowserDownload(safeName, objectUrl);
    }
}

export default DownloadUtils;
