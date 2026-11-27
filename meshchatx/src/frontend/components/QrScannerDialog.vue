<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        v-if="modelValue"
        v-escape-close="requestClose"
        class="fixed inset-0 z-[220] flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs"
        @click.self="requestClose"
    >
        <div
            role="dialog"
            aria-modal="true"
            class="w-full max-w-xl rounded-2xl bg-sem-surface shadow-2xl overflow-hidden"
        >
            <div class="px-5 py-4 border-b border-sem-border flex items-center justify-between">
                <h3 class="text-lg font-bold text-sem-fg">{{ displayTitle }}</h3>
                <button
                    type="button"
                    class="text-sem-fg-muted hover:text-sem-fg"
                    :aria-label="$t('common.close')"
                    @click="requestClose"
                >
                    <MaterialDesignIcon icon-name="close" class="size-5" />
                </button>
            </div>
            <div class="p-5 space-y-3">
                <video
                    ref="scannerVideo"
                    class="w-full rounded-xl bg-black max-h-[60vh]"
                    autoplay
                    playsinline
                    muted
                ></video>
                <div class="text-sm text-sem-fg-muted">
                    {{ scannerError || displayHint }}
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import MaterialDesignIcon from "./MaterialDesignIcon.vue";
import { useTranslateUi } from "../js/localeLoader.js";
import {
    attachStreamToVideo,
    decodeQrFromVideo,
    describeCameraError as describeQrCameraError,
    isCameraSupported,
    startCameraStream,
} from "../js/qrScannerUtils";

/**
 * Shared QR camera scanner dialog. Owns the camera stream and decode loop so
 * callers only handle the decoded payload. Emits `scan` once per distinct QR
 * value while open; callers decide whether to close (valid payload) or keep
 * scanning (invalid payload). All camera/track cleanup happens on close and
 * on unmount, including streams that resolve after the dialog was dismissed.
 */
const props = withDefaults(
    defineProps<{
        modelValue?: boolean;
        title?: string;
        hint?: string;
    }>(),
    {
        modelValue: false,
        title: "",
        hint: "",
    }
);

const emit = defineEmits<{
    "update:modelValue": [value: boolean];
    scan: [value: string];
}>();

const t = useTranslateUi();

const scannerError = ref<string | null>(null);
const starting = ref(false);

let scannerStream: MediaStream | null = null;
let scannerAnimationFrame: number | null = null;
let lastScannedValue: string | null = null;

const scannerVideo = ref<HTMLVideoElement | null>(null);

const displayTitle = computed(() => props.title || t("qr_scanner.title"));
const displayHint = computed(() => props.hint || t("qr_scanner.hint"));

watch(
    () => props.modelValue,
    async (open) => {
        if (open) {
            lastScannedValue = null;
            scannerError.value = null;
            await nextTick();
            await startScanner();
        } else {
            stopScanner();
        }
    },
    { immediate: true }
);

onBeforeUnmount(() => {
    stopScanner();
});

function requestClose() {
    emit("update:modelValue", false);
}

async function startScanner() {
    if (starting.value) {
        return;
    }
    if (!isCameraSupported()) {
        scannerError.value = t("qr_scanner.camera_not_supported");
        return;
    }
    starting.value = true;
    try {
        const stream = await startCameraStream();
        // The dialog may have been closed while the permission
        // prompt was open; release the stream instead of leaking it.
        if (!props.modelValue) {
            stream.getTracks().forEach((track) => track.stop());
            return;
        }
        if (!stream.getVideoTracks().length) {
            scannerError.value = t("qr_scanner.camera_not_found");
            stream.getTracks().forEach((track) => track.stop());
            return;
        }
        scannerStream = stream;
        const video = scannerVideo.value;
        if (!(await attachStreamToVideo(stream, video))) {
            if (props.modelValue) {
                scannerError.value = t("qr_scanner.camera_failed");
            }
            stopScanner();
            return;
        }
        if (!props.modelValue) {
            stopScanner();
            return;
        }
        detectQrLoop();
    } catch (e) {
        if (props.modelValue) {
            scannerError.value = describeCameraError(e);
        }
    } finally {
        starting.value = false;
    }
}

function detectQrLoop() {
    if (!props.modelValue) {
        return;
    }
    const video = scannerVideo.value;
    decodeQrFromVideo(video)
        .then((qr: string | null) => {
            if (!props.modelValue) {
                return;
            }
            if (qr && qr !== lastScannedValue) {
                lastScannedValue = qr;
                emit("scan", qr);
            }
            scannerAnimationFrame = requestAnimationFrame(() => detectQrLoop());
        })
        .catch(() => {
            if (props.modelValue) {
                scannerAnimationFrame = requestAnimationFrame(() => detectQrLoop());
            }
        });
}

function stopScanner() {
    if (scannerAnimationFrame != null) {
        cancelAnimationFrame(scannerAnimationFrame);
        scannerAnimationFrame = null;
    }
    if (scannerStream) {
        scannerStream.getTracks().forEach((track) => track.stop());
        scannerStream = null;
    }
}

function describeCameraError(error: unknown) {
    return describeQrCameraError(error, {
        permissionDenied: t("qr_scanner.camera_permission_denied"),
        notFound: t("qr_scanner.camera_not_found"),
        failed: t("qr_scanner.camera_failed"),
    });
}
</script>
