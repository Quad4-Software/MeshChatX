// SPDX-License-Identifier: 0BSD

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

declare module "*.css" {
    const css: string;
    export default css;
}

declare module "vis-network/styles/vis-network.css" {
    const css: string;
    export default css;
}

declare module "*.js?raw" {
    const content: string;
    export default content;
}

declare module "*.worklet.js?raw" {
    const content: string;
    export default content;
}

declare module "*MicrophoneRecorder.worklet.js?raw" {
    const content: string;
    export default content;
}

declare module "*?raw" {
    const content: string;
    export default content;
}

/**
 * Minimal typings for the untyped @browsermt/bergamot-translator package.
 * Only the surface MeshChatX touches is declared.
 */
declare module "@browsermt/bergamot-translator" {
    export interface TranslatorBackingOptions {
        cacheSize?: number;
        useNativeIntGemm?: boolean;
        downloadTimeout?: number;
        registryUrl?: string;
        pivotLanguage?: string;
        onerror?: (err: Error) => void;
        [key: string]: unknown;
    }

    export class TranslatorBacking {
        constructor(options?: TranslatorBackingOptions);
        options: TranslatorBackingOptions;
        registryUrl: string;
        registry: Promise<unknown>;
        buffers: Map<unknown, unknown>;
        pivotLanguage: string | null;
        models: Map<unknown, unknown>;
        onerror: (err: Error) => void;
        loadWorker(): Promise<{ worker: Worker; exports: unknown }>;
        loadModelRegistery(): Promise<unknown>;
        fetch(url: string, checksum?: string, extra?: { signal?: AbortSignal }): Promise<ArrayBuffer>;
        hexToBase64(hexstring: string): string;
    }

    export interface BergamotTranslateRequest {
        from: string;
        to: string;
        text: string;
        html?: boolean;
    }

    export interface BergamotTranslateOptions {
        signal?: AbortSignal;
    }

    export interface BergamotTranslateResult {
        target: { text: string };
        [key: string]: unknown;
    }

    export class LatencyOptimisedTranslator {
        constructor(options?: TranslatorBackingOptions, backing?: TranslatorBacking);
        translate(
            request: BergamotTranslateRequest,
            options?: BergamotTranslateOptions
        ): Promise<BergamotTranslateResult>;
        delete(): Promise<void>;
    }
}
