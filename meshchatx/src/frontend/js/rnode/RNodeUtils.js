export default class RNodeUtils {
    /**
     * Waits for the provided milliseconds, and then resolves.
     * @param millis
     * @returns {Promise<void>}
     */
    static async sleepMillis(millis) {
        await new Promise((resolve) => {
            setTimeout(resolve, millis);
        });
    }

    static bytesToHex(bytes) {
        for (var hex = [], i = 0; i < bytes.length; i++) {
            var current = bytes[i] < 0 ? bytes[i] + 256 : bytes[i];
            hex.push((current >>> 4).toString(16));
            hex.push((current & 0xf).toString(16));
        }
        return hex.join("");
    }

    static md5(data) {
        // We will use CryptoJS if available on window, or we might need to import it.
        // For now, let's assume we will import it or it will be provided.
        // In the original it was using CryptoJS.MD5
        if (typeof window !== "undefined" && window.CryptoJS) {
            var bytes = [];
            const hash = window.CryptoJS.MD5(window.CryptoJS.enc.Hex.parse(this.bytesToHex(data)));
            for (var i = 0; i < hash.sigBytes; i++) {
                bytes.push((hash.words[i >>> 2] >>> (24 - (i % 4) * 8)) & 0xff);
            }
            return bytes;
        }
        throw new Error("CryptoJS not found");
    }

    static packUInt32BE(value) {
        const buffer = new ArrayBuffer(4);
        const view = new DataView(buffer);
        view.setUint32(0, value, false);
        return new Uint8Array(buffer);
    }

    static unpackUInt32BE(byteArray) {
        const buffer = new Uint8Array(byteArray).buffer;
        const view = new DataView(buffer);
        return view.getUint32(0, false);
    }
}
