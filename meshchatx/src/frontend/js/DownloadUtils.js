function isAndroidSaveBridge() {
    return (
        typeof window !== "undefined" &&
        window.MeshChatXAndroid != null &&
        typeof window.MeshChatXAndroid.saveDownload === "function"
    );
}

class DownloadUtils {
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
