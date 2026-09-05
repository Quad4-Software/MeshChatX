// SPDX-License-Identifier: 0BSD

/** @param {File|null|undefined} file */
export function isWasmUploadFile(file) {
    if (!file) {
        return false;
    }
    const name = String(file.name || "").toLowerCase();
    if (name.endsWith(".wasm")) {
        return true;
    }
    const type = String(file.type || "").toLowerCase();
    return type === "application/wasm" || type === "application/octet-stream";
}

/** @param {DataTransfer|null|undefined} dataTransfer */
export function pickWasmFileFromDataTransfer(dataTransfer) {
    if (!dataTransfer) {
        return null;
    }
    const files = dataTransfer.files;
    if (files && files.length) {
        const picked = pickWasmFileFromFileList(files);
        if (picked) {
            return picked;
        }
    }
    const items = dataTransfer.items;
    if (items && items.length) {
        for (let i = 0; i < items.length; i++) {
            const item = items[i];
            if (item && item.kind === "file") {
                const file = item.getAsFile();
                if (isWasmUploadFile(file)) {
                    return file;
                }
            }
        }
    }
    return null;
}

/** @param {ClipboardEvent|{ clipboardData?: DataTransfer|null }} event */
export function pickWasmFileFromClipboardEvent(event) {
    const dataTransfer = event?.clipboardData;
    return pickWasmFileFromDataTransfer(dataTransfer);
}

/** @param {FileList|File[]|null|undefined} files */
export function pickWasmFileFromFileList(files) {
    if (!files || !files.length) {
        return null;
    }
    for (let i = 0; i < files.length; i++) {
        const file = typeof files.item === "function" ? files.item(i) : files[i];
        if (isWasmUploadFile(file)) {
            return file;
        }
    }
    return null;
}
