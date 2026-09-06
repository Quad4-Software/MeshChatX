// SPDX-License-Identifier: 0BSD

export function isWasmUploadFile(file: File | null | undefined): boolean {
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

export function pickWasmFileFromDataTransfer(dataTransfer: DataTransfer | null | undefined): File | null {
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

export function pickWasmFileFromClipboardEvent(
    event: ClipboardEvent | { clipboardData?: DataTransfer | null }
): File | null {
    const dataTransfer = event?.clipboardData;
    return pickWasmFileFromDataTransfer(dataTransfer);
}

export function pickWasmFileFromFileList(files: FileList | File[] | null | undefined): File | null {
    if (!files || !files.length) {
        return null;
    }
    for (let i = 0; i < files.length; i++) {
        const file =
            typeof (files as FileList).item === "function" ? (files as FileList).item(i) : (files as File[])[i];
        if (isWasmUploadFile(file)) {
            return file;
        }
    }
    return null;
}
