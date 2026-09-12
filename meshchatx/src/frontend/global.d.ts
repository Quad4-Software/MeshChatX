import type { createApiClient } from "./js/apiClient.js";

declare global {
    interface Window {
        /** Shared API client instance created in main.js. */
        api: ReturnType<typeof createApiClient>;
        /** Electron preload bridge, present only in the desktop shell. */
        electron?: any;
        /** Android WebView bridge, present only in the Android shell. */
        MeshChatXAndroid?: any;
        /** Native wav attachment callback registry for the Android bridge. */
        __meshchatXNative?: any;
    }

    /** Codec2 recorder loaded from public/assets/js/codec2-emscripten/. */
    const Codec2MicrophoneRecorder: any;
    /** Codec2 wasm helpers loaded from public/assets/js/codec2-emscripten/. */
    const Codec2Lib: any;
}

export {};
