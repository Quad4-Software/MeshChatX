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

<script>
import MaterialDesignIcon from "./MaterialDesignIcon.vue";
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
export default {
    name: "QrScannerDialog",
    components: {
        MaterialDesignIcon,
    },
    props: {
        modelValue: {
            type: Boolean,
            default: false,
        },
        title: {
            type: String,
            default: "",
        },
        hint: {
            type: String,
            default: "",
        },
    },
    emits: ["update:modelValue", "scan"],
    data() {
        return {
            scannerError: null,
            scannerStream: null,
            scannerAnimationFrame: null,
            lastScannedValue: null,
            starting: false,
        };
    },
    computed: {
        displayTitle() {
            return this.title || this.$t("qr_scanner.title");
        },
        displayHint() {
            return this.hint || this.$t("qr_scanner.hint");
        },
    },
    watch: {
        modelValue: {
            immediate: true,
            async handler(open) {
                if (open) {
                    this.lastScannedValue = null;
                    this.scannerError = null;
                    await this.$nextTick();
                    await this.startScanner();
                } else {
                    this.stopScanner();
                }
            },
        },
    },
    beforeUnmount() {
        this.stopScanner();
    },
    methods: {
        requestClose() {
            this.$emit("update:modelValue", false);
        },
        async startScanner() {
            if (this.starting) {
                return;
            }
            if (!isCameraSupported()) {
                this.scannerError = this.$t("qr_scanner.camera_not_supported");
                return;
            }
            this.starting = true;
            try {
                const stream = await startCameraStream();
                // The dialog may have been closed while the permission
                // prompt was open; release the stream instead of leaking it.
                if (!this.modelValue) {
                    stream.getTracks().forEach((track) => track.stop());
                    return;
                }
                if (!stream.getVideoTracks().length) {
                    this.scannerError = this.$t("qr_scanner.camera_not_found");
                    stream.getTracks().forEach((track) => track.stop());
                    return;
                }
                this.scannerStream = stream;
                const video = this.$refs.scannerVideo;
                if (!(await attachStreamToVideo(stream, video))) {
                    if (this.modelValue) {
                        this.scannerError = this.$t("qr_scanner.camera_failed");
                    }
                    this.stopScanner();
                    return;
                }
                if (!this.modelValue) {
                    this.stopScanner();
                    return;
                }
                this.detectQrLoop();
            } catch (e) {
                if (this.modelValue) {
                    this.scannerError = this.describeCameraError(e);
                }
            } finally {
                this.starting = false;
            }
        },
        detectQrLoop() {
            if (!this.modelValue) {
                return;
            }
            const video = this.$refs.scannerVideo;
            decodeQrFromVideo(video)
                .then((qr) => {
                    if (!this.modelValue) {
                        return;
                    }
                    if (qr && qr !== this.lastScannedValue) {
                        this.lastScannedValue = qr;
                        this.$emit("scan", qr);
                    }
                    this.scannerAnimationFrame = requestAnimationFrame(() => this.detectQrLoop());
                })
                .catch(() => {
                    if (this.modelValue) {
                        this.scannerAnimationFrame = requestAnimationFrame(() => this.detectQrLoop());
                    }
                });
        },
        stopScanner() {
            if (this.scannerAnimationFrame != null) {
                cancelAnimationFrame(this.scannerAnimationFrame);
                this.scannerAnimationFrame = null;
            }
            if (this.scannerStream) {
                this.scannerStream.getTracks().forEach((track) => track.stop());
                this.scannerStream = null;
            }
        },
        describeCameraError(error) {
            return describeQrCameraError(error, {
                permissionDenied: this.$t("qr_scanner.camera_permission_denied"),
                notFound: this.$t("qr_scanner.camera_not_found"),
                failed: this.$t("qr_scanner.camera_failed"),
            });
        },
    },
};
</script>
