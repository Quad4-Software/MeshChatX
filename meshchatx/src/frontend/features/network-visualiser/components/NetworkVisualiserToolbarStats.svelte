<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";

    interface Props {
        nodeCount?: number;
        edgeCount?: number;
        onlineInterfaceCount?: number;
        offlineInterfaceCount?: number;
    }

    let { nodeCount = 0, edgeCount = 0, onlineInterfaceCount = 0, offlineInterfaceCount = 0 }: Props = $props();
</script>

<div class="grid grid-cols-2 gap-3 pt-2">
    <div class="bg-gray-50/50 dark:bg-zinc-800/50 rounded-xl p-3 border border-gray-100 dark:border-zinc-700/50">
        <div class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-wider mb-1">
            {t("visualiser.nodes")}
        </div>
        <div class="text-lg font-bold text-sem-accent">{nodeCount}</div>
    </div>
    <div class="bg-gray-50/50 dark:bg-zinc-800/50 rounded-xl p-3 border border-gray-100 dark:border-zinc-700/50">
        <div class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-wider mb-1">
            {t("visualiser.links")}
        </div>
        <div class="text-lg font-bold text-emerald-600 dark:text-emerald-400">{edgeCount}</div>
    </div>
</div>

<div class="bg-zinc-950/5 dark:bg-white/5 rounded-xl p-3 border border-gray-100 dark:border-zinc-700/50">
    <div class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-wider mb-2">
        {t("visualiser.interfaces")}
    </div>
    <div class="flex items-center gap-4">
        <div class="flex items-center gap-1.5">
            <div class="w-2 h-2 rounded-full bg-emerald-500"></div>
            <span class="text-xs font-bold text-sem-fg-muted">{onlineInterfaceCount} {t("visualiser.online")}</span>
        </div>
        <div class="flex items-center gap-1.5">
            <div class="w-2 h-2 rounded-full bg-red-500"></div>
            <span class="text-xs font-bold text-sem-fg-muted">{offlineInterfaceCount} {t("visualiser.offline")}</span>
        </div>
    </div>
</div>
