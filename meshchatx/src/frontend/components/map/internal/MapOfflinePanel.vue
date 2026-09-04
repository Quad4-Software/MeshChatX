<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="space-y-3">
        <div class="flex items-center bg-sem-surface-muted rounded-lg p-0.5">
            <button
                type="button"
                class="flex-1 px-2 py-1.5 text-[11px] font-medium rounded-md"
                :class="!offlineEnabled ? 'bg-white dark:bg-zinc-700 text-blue-600' : 'text-gray-500'"
                @click="$emit('toggle-offline', false)"
            >
                {{ $t("map.online_mode") }}
            </button>
            <button
                type="button"
                class="flex-1 px-2 py-1.5 text-[11px] font-medium rounded-md"
                :class="offlineEnabled ? 'bg-white dark:bg-zinc-700 text-blue-600' : 'text-gray-500'"
                @click="$emit('toggle-offline', true)"
            >
                {{ $t("map.offline_mode") }}
            </button>
        </div>
        <label class="flex items-center justify-between text-[11px] text-sem-fg-muted">
            <span>{{ $t("map.caching_enabled") }}</span>
            <input :checked="cachingEnabled" type="checkbox" @change="$emit('toggle-caching', $event.target.checked)" />
        </label>
        <button
            type="button"
            class="w-full py-2 text-[10px] font-semibold uppercase rounded-lg bg-blue-500 text-white"
            @click="$emit('upload')"
        >
            {{ $t("map.upload_mbtiles") }}
        </button>
        <div
            v-if="offlineEnabled && !hasOfflineMap"
            class="rounded-lg border border-amber-500/40 bg-amber-500/10 p-2 space-y-2"
        >
            <div class="text-[11px] text-sem-fg leading-snug">{{ $t("map.offline_empty_hint") }}</div>
            <button
                type="button"
                class="w-full py-1.5 text-[10px] font-semibold uppercase rounded-lg border border-sem-border"
                @click="$emit('restore-starter')"
            >
                {{ $t("map.restore_starter_tiles") }}
            </button>
        </div>
        <p v-if="offlineEnabled && hasOfflineMap" class="text-[10px] text-sem-fg-muted leading-snug">
            {{ $t("map.starter_attribution") }}
        </p>
        <button
            type="button"
            class="w-full py-2 text-[10px] font-semibold uppercase rounded-lg border border-sem-border"
            @click="$emit('export-region')"
        >
            {{ $t("map.data_export_region") }}
        </button>
        <button
            type="button"
            class="w-full py-2 text-[10px] font-semibold uppercase rounded-lg border border-sem-border"
            @click="$emit('clear-cache')"
        >
            {{ $t("map.clear_cache") }}
        </button>
        <label class="block text-[11px] text-sem-fg-muted space-y-1">
            <span>{{ $t("map.storage_path") }}</span>
            <input
                :value="mbtilesDir"
                type="text"
                class="w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-[11px] font-mono"
                @blur="$emit('save-dir', $event.target.value)"
            />
        </label>
        <div
            v-for="file in mbtilesList"
            :key="file.name"
            class="flex items-center justify-between rounded-lg border border-sem-border p-2"
        >
            <div class="min-w-0">
                <div class="text-[11px] font-semibold truncate">{{ file.name }}</div>
                <div class="text-[9px] text-gray-500">{{ ((file.size || 0) / 1024 / 1024).toFixed(1) }} MB</div>
            </div>
            <div class="flex items-center gap-1">
                <button
                    v-if="!file.is_active"
                    type="button"
                    class="p-1 text-blue-500"
                    @click="$emit('set-active', file.name)"
                >
                    {{ $t("map.set_active") }}
                </button>
                <button type="button" class="p-1 text-red-500" @click="$emit('delete-file', file.name)">
                    {{ $t("map.delete") }}
                </button>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    name: "MapOfflinePanel",
    props: {
        offlineEnabled: { type: Boolean, default: false },
        cachingEnabled: { type: Boolean, default: true },
        mbtilesList: { type: Array, default: () => [] },
        mbtilesDir: { type: String, default: "" },
        hasOfflineMap: { type: Boolean, default: false },
    },
    emits: [
        "toggle-offline",
        "toggle-caching",
        "upload",
        "set-active",
        "delete-file",
        "save-dir",
        "clear-cache",
        "export-region",
        "restore-starter",
    ],
};
</script>
