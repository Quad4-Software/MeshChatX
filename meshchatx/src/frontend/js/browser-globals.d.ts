// SPDX-License-Identifier: 0BSD

declare global {
    interface Window {
        api: import("./apiClient.js").ApiClient;
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

    const __GEO_WASM_SRI_WASM__: string;
    const __GEO_WASM_SRI_EXEC__: string;
    const __MICRON_WASM_SRI_WASM__: string;
    const __MICRON_WASM_SRI_EXEC__: string;
    const __VISUALISER_WASM_SRI_WASM__: string;
    const __VISUALISER_WASM_SRI_EXEC__: string;

    const Codec2MicrophoneRecorder: {
        new (): {
            codec2Mode: string;
            start: () => Promise<boolean>;
            stop: () => Promise<ArrayBuffer>;
        };
    };

    const Codec2Lib: {
        runDecode: (mode: string, bytes: Uint8Array) => Promise<ArrayBuffer>;
        rawToWav: (bytes: ArrayBuffer) => Promise<ArrayBuffer>;
    };
}

declare module "*.css";
declare module "vis-network/styles/vis-network.css";

declare module "*.js?raw" {
    const content: string;
    export default content;
}

declare module "*.worklet.js?raw" {
    const content: string;
    export default content;
}

declare module "*?raw" {
    const content: string;
    export default content;
}

export {};
