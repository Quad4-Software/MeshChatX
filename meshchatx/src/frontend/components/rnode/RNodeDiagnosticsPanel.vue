<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        v-if="diagnostics"
        class="border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 rounded-lg overflow-hidden"
    >
        <div class="px-4 sm:px-6 py-4 border-b border-gray-100 dark:border-zinc-800 flex items-center gap-2">
            <MaterialDesignIcon icon-name="stethoscope" class="size-5 text-emerald-500" />
            <h3 class="font-bold text-gray-900 dark:text-zinc-100">
                {{ $t("tools.rnode_flasher.diagnostics.title") }}
            </h3>
            <span
                v-if="hasIssues"
                class="ml-auto px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300"
            >
                {{ $t("tools.rnode_flasher.diagnostics.needs_attention") }}
            </span>
            <span
                v-else
                class="ml-auto px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300"
            >
                {{ $t("tools.rnode_flasher.diagnostics.healthy") }}
            </span>
        </div>

        <dl class="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-3 p-4 sm:p-6 text-xs">
            <div v-for="row in summaryRows" :key="row.key" class="space-y-0.5 min-w-0">
                <dt class="text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-zinc-500">
                    {{ $t(row.labelKey) }}
                </dt>
                <dd class="font-mono text-gray-800 dark:text-zinc-200 break-all">
                    {{ row.value || "—" }}
                </dd>
            </div>
        </dl>

        <div
            v-if="hasIssues"
            class="border-t border-gray-100 dark:border-zinc-800 bg-amber-50/40 dark:bg-amber-900/10 px-4 sm:px-6 py-4 space-y-2"
        >
            <div class="text-[10px] font-bold uppercase tracking-wider text-amber-700 dark:text-amber-300">
                {{ $t("tools.rnode_flasher.diagnostics.issues_detected") }}
            </div>
            <ul class="list-disc pl-4 text-xs text-amber-800 dark:text-amber-200 space-y-1">
                <li v-for="key in diagnostics.suggestionKeys" :key="key">{{ $t(key) }}</li>
            </ul>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

export default {
    name: "RNodeDiagnosticsPanel",
    components: { MaterialDesignIcon },
    props: {
        diagnostics: { type: Object, default: null },
    },
    computed: {
        hasIssues() {
            return Array.isArray(this.diagnostics?.issues) && this.diagnostics.issues.length > 0;
        },
        summaryRows() {
            const s = this.diagnostics?.summary || {};
            return [
                {
                    key: "firmware_version",
                    labelKey: "tools.rnode_flasher.diagnostics.firmware_version",
                    value: s.firmware_version,
                },
                {
                    key: "platform",
                    labelKey: "tools.rnode_flasher.diagnostics.platform",
                    value: s.platform != null ? `0x${s.platform.toString(16).padStart(2, "0")}` : null,
                },
                {
                    key: "board",
                    labelKey: "tools.rnode_flasher.diagnostics.board",
                    value: s.board != null ? `0x${s.board.toString(16).padStart(2, "0")}` : null,
                },
                {
                    key: "is_provisioned",
                    labelKey: "tools.rnode_flasher.diagnostics.provisioned",
                    value: s.is_provisioned ? "yes" : "no",
                },
                {
                    key: "product",
                    labelKey: "tools.rnode_flasher.diagnostics.product",
                    value: s.product != null ? `0x${s.product.toString(16).padStart(2, "0")}` : null,
                },
                {
                    key: "model",
                    labelKey: "tools.rnode_flasher.diagnostics.model",
                    value: s.model != null ? `0x${s.model.toString(16).padStart(2, "0")}` : null,
                },
                {
                    key: "fw_hash",
                    labelKey: "tools.rnode_flasher.diagnostics.firmware_hash",
                    value: s.firmware_hash ? s.firmware_hash.slice(0, 16) : null,
                },
                {
                    key: "target_hash",
                    labelKey: "tools.rnode_flasher.diagnostics.target_hash",
                    value: s.target_firmware_hash ? s.target_firmware_hash.slice(0, 16) : null,
                },
            ];
        },
    },
};
</script>
