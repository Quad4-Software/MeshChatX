// SPDX-License-Identifier: 0BSD

interface Window {
    api: {
        get: (url: string, config?: Record<string, unknown>) => Promise<{ data?: any }>;
        post: (url: string, body?: unknown, config?: Record<string, unknown>) => Promise<{ data?: any }>;
        patch: (url: string, body?: unknown, config?: Record<string, unknown>) => Promise<{ data?: any }>;
        put?: (url: string, body?: unknown, config?: Record<string, unknown>) => Promise<{ data?: any }>;
        delete: (url: string, config?: Record<string, unknown>) => Promise<{ data?: any }>;
        isCancel?: (e: unknown) => boolean;
    };
    electron?: any;
    MeshChatXAndroid?: any;
    webkitAudioContext?: typeof AudioContext;
    DOMPurify?: any;
    BarcodeDetector?: any;
    zip?: any;
    CryptoJS?: any;
    enableHeapMonitor?: (intervalMs?: number) => void;
    disableHeapMonitor?: () => void;
    heapSnapshot?: () => unknown;
    __meshchatxMicronCopyFix?: boolean;
}

interface ImportMeta {
    env: Record<string, any>;
    glob: (pattern: string, options?: Record<string, any>) => Record<string, any>;
}

interface Performance {
    memory?: {
        usedJSHeapSize: number;
        totalJSHeapSize: number;
        jsHeapSizeLimit: number;
    };
}

interface Navigator {
    brave?: unknown;
    getBattery?: () => Promise<any>;
}

interface MediaTrackCapabilities {
    focusMode?: string[];
}

interface MediaTrackConstraintSet {
    focusMode?: string;
}

declare const __GEO_WASM_SRI_WASM__: string;
declare const __GEO_WASM_SRI_EXEC__: string;
declare const __MICRON_WASM_SRI_WASM__: string;
declare const __MICRON_WASM_SRI_EXEC__: string;
declare const __VISUALISER_WASM_SRI_WASM__: string;
declare const __VISUALISER_WASM_SRI_EXEC__: string;

declare const Codec2MicrophoneRecorder: {
    new (): {
        codec2Mode: string;
        start: () => Promise<boolean>;
        stop: () => Promise<ArrayBuffer>;
    };
};

declare const Codec2Lib: {
    runDecode: (mode: string, bytes: Uint8Array) => Promise<ArrayBuffer>;
    rawToWav: (bytes: ArrayBuffer) => Promise<ArrayBuffer>;
};

declare module "*.css";

declare module "*?raw" {
    const content: string;
    export default content;
}
