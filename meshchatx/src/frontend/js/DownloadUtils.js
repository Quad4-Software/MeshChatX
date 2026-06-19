function isAndroidSaveBridge() {
    return (
        typeof window !== "undefined" &&
        window.MeshChatXAndroid != null &&
        typeof window.MeshChatXAndroid.saveDownload === "function"
    );
}

class DownloadUtils {
    static parseFilenameFromContentDisposition(header, defaultFilename) {
        if (!header || typeof header !== "string") {
            return defaultFilename;
        }
        const star = header.match(/filename\*=UTF-8''([^;\s]+)/i);
        if (star?.[1]) {
            try {
                return decodeURIComponent(star[1]);
            } catch {
                // fall through
            }
        }
        const plain = header.match(/filename="?([^";\n]+)"?/i);
        if (plain?.[1]) {
            return plain[1].trim();
        }
        return defaultFilename;
    }

    static async downloadFromApiResponse(response, defaultFilename) {
        const headers = response?.headers || {};
        const cd = headers["content-disposition"] || headers["Content-Disposition"];
        const filename = DownloadUtils.parseFilenameFromContentDisposition(cd, defaultFilename);
        const type = headers["content-type"] || headers["Content-Type"] || "application/octet-stream";
        const blob = new Blob([response.data], { type });
        await DownloadUtils.downloadFile(filename, blob);
    }

    static _blobToBase64(blob) {
        return new Promise((resolve, reject) => {
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
        if (isAndroidSaveBridge()) {
            window.MeshChatXAndroid.saveDownload(filename, fileBytesBase64);
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
        DownloadUtils._triggerBrowserDownload(filename, objectUrl);
    }

    static async downloadFile(filename, blob) {
        if (isAndroidSaveBridge()) {
            const b64 = await DownloadUtils._blobToBase64(blob);
            window.MeshChatXAndroid.saveDownload(filename, b64);
            return;
        }
        const objectUrl = URL.createObjectURL(blob);
        DownloadUtils._triggerBrowserDownload(filename, objectUrl);
    }
}

export default DownloadUtils;
