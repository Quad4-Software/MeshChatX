<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    interface Props {
        onaction?: (actionId: string) => void;
    }

    let { onaction }: Props = $props();
</script>

<div class="border border-sem-border bg-sem-surface rounded-2xl shadow-xl overflow-hidden">
    <div class="px-4 sm:px-6 py-4 border-b border-sem-border flex items-center gap-2">
        <MaterialDesignIcon iconName="bluetooth" class="size-5 text-blue-500" />
        <h3 class="font-bold text-sem-fg">
            {t("tools.rnode_flasher.configure_bluetooth")}
        </h3>
    </div>
    <div class="p-4 sm:p-6 space-y-4">
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
            <button
                type="button"
                class="inline-flex items-center justify-center gap-1.5 rounded-xl bg-sem-surface-muted hover:bg-gray-200 dark:hover:bg-sem-surface-muted px-3 py-2.5 text-[11px] font-bold text-sem-fg-muted border border-sem-border transition-all active:scale-95 cursor-pointer"
                onclick={() => onaction?.("enable-bluetooth")}
            >
                <MaterialDesignIcon iconName="bluetooth-connect" class="size-4" />
                {t("tools.rnode_flasher.enable")}
            </button>
            <button
                type="button"
                class="inline-flex items-center justify-center gap-1.5 rounded-xl bg-sem-surface-muted hover:bg-gray-200 dark:hover:bg-sem-surface-muted px-3 py-2.5 text-[11px] font-bold text-sem-fg-muted border border-sem-border transition-all active:scale-95 cursor-pointer"
                onclick={() => onaction?.("disable-bluetooth")}
            >
                <MaterialDesignIcon iconName="bluetooth-off" class="size-4" />
                {t("tools.rnode_flasher.disable")}
            </button>
            <button
                type="button"
                class="col-span-2 sm:col-span-1 inline-flex items-center justify-center gap-1.5 rounded-xl bg-blue-500 hover:bg-blue-600 px-3 py-2.5 text-[11px] font-bold text-white! border-none! transition-all active:scale-95 cursor-pointer"
                onclick={() => onaction?.("pair-bluetooth")}
            >
                <MaterialDesignIcon iconName="key-link" class="size-4" />
                {t("tools.rnode_flasher.start_pairing")}
            </button>
        </div>
        <p class="text-[10px] text-sem-fg-muted leading-relaxed uppercase tracking-wider">
            {t("tools.rnode_flasher.bluetooth_restart_warning")}
        </p>
    </div>
</div>
