<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="space-y-3 rounded-xl border border-sem-border bg-gray-50/50 dark:bg-zinc-900/40 p-3">
        <div class="flex items-center justify-between gap-2">
            <span class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest">{{
                $t("map.remote_overlays_title")
            }}</span>
            <button
                type="button"
                class="text-[10px] font-bold uppercase text-sem-accent disabled:opacity-40"
                :disabled="loading || disabled"
                @click="reload"
            >
                {{ $t("map.remote_overlays_reload") }}
            </button>
        </div>

        <div class="grid grid-cols-1 gap-2">
            <label class="text-[10px] text-sem-fg-muted space-y-1">
                <span>{{ $t("map.remote_overlays_kind") }}</span>
                <select
                    v-model="kind"
                    class="w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-[11px]"
                >
                    <option value="nomadnet_file">NomadNet /file/</option>
                    <option value="rngit_files">RNGit sparse</option>
                </select>
            </label>
            <label class="text-[10px] text-sem-fg-muted space-y-1">
                <span>{{ $t("map.remote_overlays_url") }}</span>
                <input
                    v-model="url"
                    type="text"
                    class="w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-[11px]"
                    :placeholder="kind === 'rngit_files' ? 'rns://hash/group/repo' : 'hash:/file/maps/layer.geojson'"
                />
            </label>
            <label v-if="kind === 'rngit_files'" class="text-[10px] text-sem-fg-muted space-y-1">
                <span>{{ $t("map.remote_overlays_paths") }}</span>
                <textarea
                    v-model="pathsText"
                    rows="3"
                    class="w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-[11px] font-mono"
                    placeholder="maps/layer.geojson"
                />
            </label>
            <label v-if="kind === 'rngit_files'" class="text-[10px] text-sem-fg-muted space-y-1">
                <span>{{ $t("map.remote_overlays_ref") }}</span>
                <input
                    v-model="refName"
                    type="text"
                    class="w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-[11px]"
                    placeholder="HEAD / tag / commit"
                />
            </label>
            <label class="text-[10px] text-sem-fg-muted space-y-1">
                <span>{{ $t("map.remote_overlays_refresh_interval") }}</span>
                <input
                    v-model.number="refreshInterval"
                    type="number"
                    min="0"
                    class="w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-[11px]"
                />
            </label>
            <button
                type="button"
                class="py-2 px-2 text-[10px] font-bold uppercase rounded-lg bg-blue-500 hover:bg-blue-600 text-white disabled:opacity-40"
                :disabled="disabled || importing || !url.trim()"
                @click="importSources"
            >
                {{ importing ? $t("map.remote_overlays_importing") : $t("map.remote_overlays_import") }}
            </button>
            <p v-if="jobPhase" class="text-[9px] text-sem-fg-muted">{{ jobPhase }}</p>
        </div>

        <div v-if="overlays.length" class="space-y-2 border-t border-sem-border pt-2">
            <div
                v-for="overlay in overlays"
                :key="overlay.id"
                class="rounded-lg border border-sem-border bg-sem-surface/60 p-2 space-y-1.5"
            >
                <div class="flex items-start justify-between gap-2">
                    <div class="min-w-0">
                        <div class="text-[11px] font-semibold text-sem-fg truncate">
                            {{ overlay.name }}
                        </div>
                        <div class="text-[9px] text-sem-fg-muted truncate">
                            {{ overlay.kind }} · {{ overlay.status }}
                            <span v-if="overlay.format"> · {{ overlay.format }}</span>
                        </div>
                        <div v-if="overlay.last_error" class="text-[9px] text-red-500 truncate">
                            {{ overlay.last_error }}
                        </div>
                    </div>
                    <label class="flex items-center gap-1 text-[9px] text-gray-500 shrink-0">
                        <input
                            type="checkbox"
                            :checked="Boolean(overlay.visible)"
                            @change="toggleVisible(overlay, $event.target.checked)"
                        />
                        {{ $t("map.remote_overlays_visible") }}
                    </label>
                </div>
                <div class="flex flex-wrap gap-1">
                    <button
                        type="button"
                        class="px-1.5 py-1 text-[9px] font-bold uppercase rounded bg-sem-surface-muted"
                        :disabled="disabled"
                        @click="refresh(overlay)"
                    >
                        {{ $t("map.remote_overlays_refresh") }}
                    </button>
                    <button
                        type="button"
                        class="px-1.5 py-1 text-[9px] font-bold uppercase rounded bg-sem-surface-muted"
                        :disabled="disabled || overlay.status !== 'ready'"
                        @click="$emit('export-overlay', { id: overlay.id, format: 'geojson' })"
                    >
                        GeoJSON
                    </button>
                    <button
                        type="button"
                        class="px-1.5 py-1 text-[9px] font-bold uppercase rounded bg-sem-surface-muted"
                        :disabled="disabled || overlay.status !== 'ready'"
                        @click="$emit('export-overlay', { id: overlay.id, format: 'kml' })"
                    >
                        KML
                    </button>
                    <button
                        type="button"
                        class="px-1.5 py-1 text-[9px] font-bold uppercase rounded bg-sem-surface-muted"
                        :disabled="disabled || overlay.status !== 'ready'"
                        @click="$emit('export-overlay', { id: overlay.id, format: 'kmz' })"
                    >
                        KMZ
                    </button>
                    <button
                        type="button"
                        class="px-1.5 py-1 text-[9px] font-bold uppercase rounded bg-sem-surface-muted"
                        :disabled="disabled || overlay.status !== 'ready'"
                        @click="$emit('copy-overlay-to-drawings', overlay)"
                    >
                        {{ $t("map.remote_overlays_copy_drawings") }}
                    </button>
                    <button
                        type="button"
                        class="px-1.5 py-1 text-[9px] font-bold uppercase rounded bg-red-50 text-red-600 dark:bg-red-950/40 dark:text-red-400"
                        :disabled="disabled"
                        @click="remove(overlay)"
                    >
                        {{ $t("map.remote_overlays_delete") }}
                    </button>
                </div>
            </div>
        </div>
        <p v-else class="text-[9px] text-sem-fg-muted">{{ $t("map.remote_overlays_empty") }}</p>
    </div>
</template>

<script>
export default {
    name: "MapRemoteOverlayPanel",
    props: {
        disabled: { type: Boolean, default: false },
    },
    emits: ["overlays-changed", "export-overlay", "copy-overlay-to-drawings", "error"],
    data() {
        return {
            kind: "nomadnet_file",
            url: "",
            pathsText: "",
            refName: "HEAD",
            refreshInterval: 0,
            overlays: [],
            loading: false,
            importing: false,
            jobPhase: "",
            pollTimer: null,
            activeJobId: null,
            jobGeneration: 0,
        };
    },
    mounted() {
        this.reload();
    },
    beforeUnmount() {
        this.clearPoll();
    },
    methods: {
        clearPoll() {
            if (this.pollTimer) {
                clearInterval(this.pollTimer);
                this.pollTimer = null;
            }
        },
        async reload() {
            this.loading = true;
            try {
                const res = await window.api.get("/api/v1/map/overlays");
                this.overlays = res?.overlays || [];
                this.$emit("overlays-changed", this.overlays);
            } catch (e) {
                this.$emit("error", e);
            } finally {
                this.loading = false;
            }
        },
        async importSources() {
            const body = {
                kind: this.kind,
                url: this.url.trim(),
                refresh_interval_seconds: Number(this.refreshInterval) || 0,
            };
            if (this.kind === "rngit_files") {
                body.ref = this.refName || "HEAD";
                body.paths = this.pathsText
                    .split("\n")
                    .map((l) => l.trim())
                    .filter(Boolean);
            }
            this.importing = true;
            this.jobPhase = "queued";
            try {
                const res = await window.api.post("/api/v1/map/overlays", body);
                this.overlays = res?.overlays || this.overlays;
                this.$emit("overlays-changed", this.overlays);
                if (res?.job_id) {
                    this.watchJob(res.job_id);
                }
            } catch (e) {
                this.$emit("error", e);
                this.importing = false;
                this.jobPhase = "";
            }
        },
        watchJob(jobId) {
            this.clearPoll();
            this.activeJobId = jobId;
            const gen = ++this.jobGeneration;
            this.pollTimer = setInterval(async () => {
                if (gen !== this.jobGeneration) {
                    return;
                }
                try {
                    const job = await window.api.get(`/api/v1/map/overlays/jobs/${jobId}`);
                    if (gen !== this.jobGeneration) {
                        return;
                    }
                    this.jobPhase = job?.phase || job?.status || "";
                    if (job?.status === "success" || job?.status === "error" || job?.status === "cancelled") {
                        this.clearPoll();
                        this.importing = false;
                        await this.reload();
                        if (job.status !== "success") {
                            this.$emit("error", job.error || job.status);
                        }
                    }
                } catch (e) {
                    this.clearPoll();
                    this.importing = false;
                    this.$emit("error", e);
                }
            }, 1000);
        },
        async refresh(overlay) {
            try {
                const res = await window.api.post(`/api/v1/map/overlays/${overlay.id}/refresh`, {});
                if (res?.job_id) {
                    this.importing = true;
                    this.watchJob(res.job_id);
                }
            } catch (e) {
                this.$emit("error", e);
            }
        },
        async toggleVisible(overlay, visible) {
            try {
                await window.api.patch(`/api/v1/map/overlays/${overlay.id}`, { visible: Boolean(visible) });
                await this.reload();
            } catch (e) {
                this.$emit("error", e);
            }
        },
        async remove(overlay) {
            try {
                await window.api.delete(`/api/v1/map/overlays/${overlay.id}`);
                await this.reload();
            } catch (e) {
                this.$emit("error", e);
            }
        },
    },
};
</script>
