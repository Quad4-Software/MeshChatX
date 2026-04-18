<template>
    <div
        v-if="visible"
        class="fixed inset-0 z-[200] flex items-center justify-center bg-black/70 p-4"
        @click.self="onCancel"
    >
        <div
            class="w-full max-w-3xl max-h-[92vh] overflow-hidden rounded-2xl bg-white dark:bg-zinc-900 shadow-2xl flex flex-col border border-gray-200 dark:border-zinc-700"
        >
            <header class="flex items-center justify-between border-b border-gray-200 dark:border-zinc-700 px-4 py-3">
                <div class="flex items-center gap-2">
                    <MaterialDesignIcon icon-name="sticker-emoji" class="size-5 text-blue-500" />
                    <h2 class="text-lg font-semibold text-gray-800 dark:text-zinc-100">
                        {{ $t("sticker_editor.title") }}
                    </h2>
                </div>
                <button
                    type="button"
                    class="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 dark:hover:bg-zinc-800"
                    @click="onCancel"
                >
                    <MaterialDesignIcon icon-name="close" class="size-5" />
                </button>
            </header>

            <div class="flex-1 overflow-y-auto p-4 grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-4">
                <div class="flex flex-col items-center gap-3">
                    <div
                        class="relative w-full max-w-[512px] aspect-square rounded-xl bg-checkerboard border border-gray-200 dark:border-zinc-700 overflow-hidden"
                    >
                        <canvas ref="canvas" class="w-full h-full" :width="canvasSize" :height="canvasSize" />
                        <div
                            v-if="busy"
                            class="absolute inset-0 flex items-center justify-center bg-black/40 text-white text-sm"
                        >
                            <div class="flex flex-col items-center gap-2">
                                <div class="size-8 border-4 border-white/50 border-t-white rounded-full animate-spin" />
                                <span>{{ busyMessage || $t("sticker_editor.processing") }}</span>
                            </div>
                        </div>
                    </div>
                    <div class="text-xs text-gray-500 dark:text-zinc-400 text-center max-w-md px-2">
                        {{ $t("sticker_editor.canvas_hint") }}
                    </div>
                </div>

                <div class="flex flex-col gap-3 text-sm">
                    <div class="flex flex-col gap-2">
                        <label class="text-xs font-semibold uppercase text-gray-500 dark:text-zinc-400">
                            {{ $t("sticker_editor.section_source") }}
                        </label>
                        <button
                            type="button"
                            class="rounded-xl border border-gray-300 dark:border-zinc-600 px-3 py-2 hover:border-blue-500 text-gray-700 dark:text-zinc-200 flex items-center gap-2"
                            @click="triggerSourceInput"
                        >
                            <MaterialDesignIcon icon-name="image-plus" class="size-4" />
                            {{ $t("sticker_editor.choose_image") }}
                        </button>
                        <input
                            ref="sourceInput"
                            type="file"
                            accept="image/png,image/jpeg,image/webp,image/bmp,image/gif"
                            class="hidden"
                            @change="onSourceFile"
                        />
                    </div>

                    <div v-if="sourceLoaded" class="flex flex-col gap-3">
                        <div class="flex flex-col gap-2">
                            <label class="text-xs font-semibold uppercase text-gray-500 dark:text-zinc-400">
                                {{ $t("sticker_editor.section_transform") }}
                            </label>
                            <label class="flex items-center justify-between gap-2">
                                <span>{{ $t("sticker_editor.scale") }}</span>
                                <input
                                    v-model.number="scale"
                                    type="range"
                                    min="0.1"
                                    max="3"
                                    step="0.01"
                                    class="flex-1 mx-2"
                                    @input="redraw"
                                />
                                <span class="w-10 text-right tabular-nums">{{ scale.toFixed(2) }}</span>
                            </label>
                            <label class="flex items-center justify-between gap-2">
                                <span>{{ $t("sticker_editor.rotation") }}</span>
                                <input
                                    v-model.number="rotation"
                                    type="range"
                                    min="-180"
                                    max="180"
                                    step="1"
                                    class="flex-1 mx-2"
                                    @input="redraw"
                                />
                                <span class="w-10 text-right tabular-nums">{{ rotation }}&deg;</span>
                            </label>
                            <div class="grid grid-cols-2 gap-2">
                                <label class="flex items-center gap-2">
                                    <input v-model="flipH" type="checkbox" @change="redraw" />
                                    {{ $t("sticker_editor.flip_h") }}
                                </label>
                                <label class="flex items-center gap-2">
                                    <input v-model="flipV" type="checkbox" @change="redraw" />
                                    {{ $t("sticker_editor.flip_v") }}
                                </label>
                            </div>
                            <button
                                type="button"
                                class="rounded-lg border border-gray-300 dark:border-zinc-600 px-2 py-1 text-xs"
                                @click="resetTransform"
                            >
                                {{ $t("sticker_editor.reset_transform") }}
                            </button>
                        </div>

                        <div class="flex flex-col gap-2">
                            <label class="text-xs font-semibold uppercase text-gray-500 dark:text-zinc-400">
                                {{ $t("sticker_editor.section_effects") }}
                            </label>
                            <button
                                type="button"
                                class="rounded-lg border border-gray-300 dark:border-zinc-600 px-2 py-1 hover:border-emerald-500"
                                :disabled="busy"
                                @click="removeBackground"
                            >
                                {{
                                    bgRemoved ? $t("sticker_editor.bg_removed") : $t("sticker_editor.remove_background")
                                }}
                            </button>
                            <label class="flex items-center justify-between gap-2">
                                <span>{{ $t("sticker_editor.white_stroke") }}</span>
                                <input
                                    v-model.number="strokeWidth"
                                    type="range"
                                    min="0"
                                    max="24"
                                    step="1"
                                    class="flex-1 mx-2"
                                    @input="redraw"
                                />
                                <span class="w-10 text-right tabular-nums">{{ strokeWidth }}px</span>
                            </label>
                            <label class="flex items-center justify-between gap-2">
                                <span>{{ $t("sticker_editor.shadow") }}</span>
                                <input
                                    v-model.number="shadowBlur"
                                    type="range"
                                    min="0"
                                    max="48"
                                    step="1"
                                    class="flex-1 mx-2"
                                    @input="redraw"
                                />
                                <span class="w-10 text-right tabular-nums">{{ shadowBlur }}px</span>
                            </label>
                        </div>

                        <div class="flex flex-col gap-2">
                            <label class="text-xs font-semibold uppercase text-gray-500 dark:text-zinc-400">
                                {{ $t("sticker_editor.section_overlay") }}
                            </label>
                            <input
                                v-model="overlayText"
                                type="text"
                                class="rounded-lg border border-gray-300 dark:border-zinc-600 px-2 py-1 bg-white dark:bg-zinc-800"
                                :placeholder="$t('sticker_editor.overlay_placeholder')"
                                @input="redraw"
                            />
                            <label class="flex items-center justify-between gap-2">
                                <span>{{ $t("sticker_editor.font_size") }}</span>
                                <input
                                    v-model.number="overlayFontSize"
                                    type="range"
                                    min="16"
                                    max="160"
                                    step="2"
                                    class="flex-1 mx-2"
                                    @input="redraw"
                                />
                                <span class="w-10 text-right tabular-nums">{{ overlayFontSize }}</span>
                            </label>
                            <label class="flex items-center justify-between gap-2">
                                <span>{{ $t("sticker_editor.overlay_y") }}</span>
                                <input
                                    v-model.number="overlayY"
                                    type="range"
                                    min="0"
                                    max="100"
                                    step="1"
                                    class="flex-1 mx-2"
                                    @input="redraw"
                                />
                                <span class="w-10 text-right tabular-nums">{{ overlayY }}%</span>
                            </label>
                            <div class="flex items-center gap-2">
                                <label class="flex items-center gap-1">
                                    <input v-model="overlayColor" type="color" class="w-7 h-7 cursor-pointer" />
                                    {{ $t("sticker_editor.text_color") }}
                                </label>
                                <label class="flex items-center gap-1">
                                    <input v-model="overlayStrokeColor" type="color" class="w-7 h-7 cursor-pointer" />
                                    {{ $t("sticker_editor.stroke_color") }}
                                </label>
                            </div>
                        </div>

                        <div class="flex flex-col gap-2">
                            <label class="text-xs font-semibold uppercase text-gray-500 dark:text-zinc-400">
                                {{ $t("sticker_editor.section_meta") }}
                            </label>
                            <input
                                v-model="stickerName"
                                type="text"
                                class="rounded-lg border border-gray-300 dark:border-zinc-600 px-2 py-1 bg-white dark:bg-zinc-800"
                                :placeholder="$t('sticker_editor.name_placeholder')"
                                maxlength="64"
                            />
                            <input
                                v-model="stickerEmoji"
                                type="text"
                                class="rounded-lg border border-gray-300 dark:border-zinc-600 px-2 py-1 bg-white dark:bg-zinc-800"
                                :placeholder="$t('sticker_editor.emoji_placeholder')"
                                maxlength="8"
                            />
                            <label class="flex items-center justify-between gap-2">
                                <span>{{ $t("sticker_editor.format") }}</span>
                                <select
                                    v-model="exportFormat"
                                    class="rounded-lg border border-gray-300 dark:border-zinc-600 px-2 py-1 bg-white dark:bg-zinc-800"
                                >
                                    <option value="webp">WebP</option>
                                    <option value="png">PNG</option>
                                </select>
                            </label>
                            <label class="flex items-center justify-between gap-2">
                                <span>{{ $t("sticker_editor.quality") }}</span>
                                <input
                                    v-model.number="exportQuality"
                                    type="range"
                                    min="0.5"
                                    max="1"
                                    step="0.01"
                                    class="flex-1 mx-2"
                                />
                                <span class="w-10 text-right tabular-nums">{{ Math.round(exportQuality * 100) }}%</span>
                            </label>
                        </div>
                    </div>
                </div>
            </div>

            <footer
                class="flex items-center justify-between gap-2 border-t border-gray-200 dark:border-zinc-700 px-4 py-3 bg-gray-50 dark:bg-zinc-900/50"
            >
                <div class="text-xs text-gray-500 dark:text-zinc-400">
                    {{
                        $t("sticker_editor.size_label", {
                            size: formattedSize,
                            limit: "512 KB",
                        })
                    }}
                </div>
                <div class="flex items-center gap-2">
                    <button
                        type="button"
                        class="rounded-lg border border-gray-300 dark:border-zinc-600 px-3 py-1.5 text-sm hover:bg-gray-100 dark:hover:bg-zinc-800"
                        @click="onCancel"
                    >
                        {{ $t("sticker_editor.cancel") }}
                    </button>
                    <button
                        type="button"
                        class="rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 py-1.5 text-sm font-medium"
                        :disabled="!sourceLoaded || busy || !canSave"
                        @click="onSave"
                    >
                        {{ $t("sticker_editor.save") }}
                    </button>
                </div>
            </footer>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils.js";

const CANVAS_SIZE = 512;
const TELEGRAM_STATIC_LIMIT = 512 * 1024;

export default {
    name: "StickerEditor",
    components: { MaterialDesignIcon },
    props: {
        visible: { type: Boolean, default: false },
        defaultPackId: { type: [Number, String, null], default: null },
        initialFile: { type: [File, Blob, null], default: null },
    },
    emits: ["close", "saved"],
    data() {
        return {
            canvasSize: CANVAS_SIZE,
            sourceImage: null,
            sourceLoaded: false,
            scale: 1,
            rotation: 0,
            flipH: false,
            flipV: false,
            strokeWidth: 0,
            shadowBlur: 0,
            overlayText: "",
            overlayFontSize: 64,
            overlayY: 90,
            overlayColor: "#ffffff",
            overlayStrokeColor: "#000000",
            stickerName: "",
            stickerEmoji: "",
            exportFormat: "webp",
            exportQuality: 0.92,
            busy: false,
            busyMessage: "",
            bgRemoved: false,
            lastBlob: null,
            bgRemovalModule: null,
        };
    },
    computed: {
        formattedSize() {
            const size = this.lastBlob ? this.lastBlob.size : 0;
            if (size <= 0) return "0 KB";
            return `${(size / 1024).toFixed(1)} KB`;
        },
        canSave() {
            return this.lastBlob && this.lastBlob.size > 0 && this.lastBlob.size <= TELEGRAM_STATIC_LIMIT;
        },
    },
    watch: {
        visible(v) {
            if (v) {
                this.resetState();
                this.$nextTick(() => {
                    if (this.initialFile) {
                        this.loadSourceFromBlob(this.initialFile);
                    }
                });
            }
        },
        exportFormat() {
            this.redraw();
        },
        exportQuality() {
            this.redraw();
        },
    },
    methods: {
        resetState() {
            this.sourceImage = null;
            this.sourceLoaded = false;
            this.scale = 1;
            this.rotation = 0;
            this.flipH = false;
            this.flipV = false;
            this.strokeWidth = 0;
            this.shadowBlur = 0;
            this.overlayText = "";
            this.stickerName = "";
            this.stickerEmoji = "";
            this.bgRemoved = false;
            this.lastBlob = null;
            const c = this.$refs.canvas;
            if (c) {
                const ctx = c.getContext("2d");
                ctx.clearRect(0, 0, c.width, c.height);
            }
        },
        resetTransform() {
            this.scale = 1;
            this.rotation = 0;
            this.flipH = false;
            this.flipV = false;
            this.redraw();
        },
        triggerSourceInput() {
            this.$refs.sourceInput?.click();
        },
        onSourceFile(event) {
            const file = event.target.files?.[0];
            if (file) this.loadSourceFromBlob(file);
            event.target.value = "";
        },
        async loadSourceFromBlob(blob) {
            const url = URL.createObjectURL(blob);
            try {
                const img = await this.loadImage(url);
                this.sourceImage = img;
                this.bgRemoved = false;
                const longest = Math.max(img.naturalWidth, img.naturalHeight) || 1;
                this.scale = Math.min(1, CANVAS_SIZE / longest);
                this.sourceLoaded = true;
                this.redraw();
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("sticker_editor.image_load_failed"));
            } finally {
                URL.revokeObjectURL(url);
            }
        },
        loadImage(src) {
            return new Promise((resolve, reject) => {
                const img = new Image();
                img.onload = () => resolve(img);
                img.onerror = reject;
                img.src = src;
            });
        },
        async redraw() {
            if (!this.sourceImage) return;
            const canvas = this.$refs.canvas;
            if (!canvas) return;
            const ctx = canvas.getContext("2d");
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            const img = this.sourceImage;
            const drawW = img.naturalWidth * this.scale;
            const drawH = img.naturalHeight * this.scale;

            ctx.save();
            ctx.translate(canvas.width / 2, canvas.height / 2);
            ctx.rotate((this.rotation * Math.PI) / 180);
            ctx.scale(this.flipH ? -1 : 1, this.flipV ? -1 : 1);

            if (this.shadowBlur > 0) {
                ctx.shadowColor = "rgba(0,0,0,0.55)";
                ctx.shadowBlur = this.shadowBlur;
                ctx.shadowOffsetX = 0;
                ctx.shadowOffsetY = Math.max(2, this.shadowBlur / 4);
            }

            if (this.strokeWidth > 0 && this.bgRemoved) {
                this.drawStrokedImage(ctx, img, drawW, drawH, this.strokeWidth);
            } else {
                ctx.drawImage(img, -drawW / 2, -drawH / 2, drawW, drawH);
            }
            ctx.restore();

            if (this.overlayText) {
                this.drawOverlayText(ctx);
            }

            await this.recomputeBlob();
        },
        drawStrokedImage(ctx, img, w, h, stroke) {
            const off = document.createElement("canvas");
            off.width = w + stroke * 2;
            off.height = h + stroke * 2;
            const oc = off.getContext("2d");
            oc.drawImage(img, stroke, stroke, w, h);
            const stamp = document.createElement("canvas");
            stamp.width = off.width;
            stamp.height = off.height;
            const sc = stamp.getContext("2d");
            for (let dx = -stroke; dx <= stroke; dx += 1) {
                for (let dy = -stroke; dy <= stroke; dy += 1) {
                    if (dx * dx + dy * dy > stroke * stroke) continue;
                    sc.drawImage(off, dx, dy);
                }
            }
            sc.globalCompositeOperation = "source-in";
            sc.fillStyle = "#ffffff";
            sc.fillRect(0, 0, stamp.width, stamp.height);
            ctx.drawImage(stamp, -stamp.width / 2, -stamp.height / 2);
            ctx.drawImage(img, -w / 2, -h / 2, w, h);
        },
        drawOverlayText(ctx) {
            const text = this.overlayText;
            const px = Math.max(8, this.overlayFontSize);
            ctx.save();
            ctx.font = `900 ${px}px "Inter", "Helvetica Neue", sans-serif`;
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            const cy = (this.overlayY / 100) * this.canvasSize;
            ctx.lineJoin = "round";
            ctx.miterLimit = 2;
            ctx.lineWidth = Math.max(2, px / 8);
            ctx.strokeStyle = this.overlayStrokeColor;
            ctx.strokeText(text, this.canvasSize / 2, cy);
            ctx.fillStyle = this.overlayColor;
            ctx.fillText(text, this.canvasSize / 2, cy);
            ctx.restore();
        },
        async recomputeBlob() {
            const canvas = this.$refs.canvas;
            if (!canvas) {
                this.lastBlob = null;
                return;
            }
            const mime = this.exportFormat === "png" ? "image/png" : "image/webp";
            const quality = this.exportFormat === "png" ? undefined : this.exportQuality;
            const blob = await new Promise((resolve) => canvas.toBlob((b) => resolve(b), mime, quality));
            this.lastBlob = blob;
        },
        async removeBackground() {
            if (!this.sourceImage) return;
            this.busy = true;
            this.busyMessage = this.$t("sticker_editor.removing_background");
            try {
                if (!this.bgRemovalModule) {
                    this.bgRemovalModule = await import("@imgly/background-removal");
                }
                const removeFn = this.bgRemovalModule.removeBackground || this.bgRemovalModule.default;
                if (!removeFn) {
                    throw new Error("background removal entrypoint not found");
                }
                const blob = await this.blobFromSourceImage();
                const cleaned = await removeFn(blob, {
                    output: { format: "image/png", quality: 0.95 },
                });
                const url = URL.createObjectURL(cleaned);
                try {
                    const img = await this.loadImage(url);
                    this.sourceImage = img;
                    this.bgRemoved = true;
                    if (this.strokeWidth === 0) {
                        this.strokeWidth = 8;
                    }
                    if (this.shadowBlur === 0) {
                        this.shadowBlur = 16;
                    }
                    await this.redraw();
                } finally {
                    URL.revokeObjectURL(url);
                }
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("sticker_editor.bg_removal_failed"));
            } finally {
                this.busy = false;
                this.busyMessage = "";
            }
        },
        async blobFromSourceImage() {
            const c = document.createElement("canvas");
            c.width = this.sourceImage.naturalWidth;
            c.height = this.sourceImage.naturalHeight;
            const ctx = c.getContext("2d");
            ctx.drawImage(this.sourceImage, 0, 0);
            return new Promise((resolve) => c.toBlob((b) => resolve(b), "image/png"));
        },
        arrayBufferToBase64(buf) {
            const bytes = new Uint8Array(buf);
            let binary = "";
            const chunk = 0x8000;
            for (let i = 0; i < bytes.length; i += chunk) {
                binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
            }
            return btoa(binary);
        },
        async onSave() {
            if (!this.lastBlob) return;
            if (this.lastBlob.size > TELEGRAM_STATIC_LIMIT) {
                ToastUtils.error(this.$t("sticker_editor.too_large"));
                return;
            }
            this.busy = true;
            this.busyMessage = this.$t("sticker_editor.saving");
            try {
                const buf = await this.lastBlob.arrayBuffer();
                const b64 = this.arrayBufferToBase64(buf);
                const payload = {
                    image_bytes: b64,
                    image_type: this.exportFormat,
                    name: this.stickerName || null,
                    emoji: this.stickerEmoji || null,
                    strict: true,
                };
                if (this.defaultPackId != null) {
                    payload.pack_id = Number(this.defaultPackId);
                }
                const r = await window.api.post("/api/v1/stickers", payload);
                ToastUtils.success(this.$t("sticker_editor.saved"));
                this.$emit("saved", r.data?.sticker || null);
                this.$emit("close");
            } catch (e) {
                const err = e?.response?.data?.error || "save_failed";
                if (err === "duplicate_sticker") {
                    ToastUtils.info(this.$t("stickers.duplicate"));
                } else {
                    ToastUtils.error(`${this.$t("sticker_editor.save_failed")}: ${err}`);
                }
            } finally {
                this.busy = false;
                this.busyMessage = "";
            }
        },
        onCancel() {
            this.$emit("close");
        },
    },
};
</script>

<style scoped>
.bg-checkerboard {
    background-image:
        linear-gradient(45deg, #d1d5db 25%, transparent 25%), linear-gradient(-45deg, #d1d5db 25%, transparent 25%),
        linear-gradient(45deg, transparent 75%, #d1d5db 75%), linear-gradient(-45deg, transparent 75%, #d1d5db 75%);
    background-size: 20px 20px;
    background-position:
        0 0,
        0 10px,
        10px -10px,
        -10px 0;
    background-color: #f3f4f6;
}
:global(.dark) .bg-checkerboard {
    background-image:
        linear-gradient(45deg, #374151 25%, transparent 25%), linear-gradient(-45deg, #374151 25%, transparent 25%),
        linear-gradient(45deg, transparent 75%, #374151 75%), linear-gradient(-45deg, transparent 75%, #374151 75%);
    background-color: #1f2937;
}
</style>
