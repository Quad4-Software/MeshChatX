<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    const ALL_ACTIONS = [
        { id: "detect", icon: "magnify", labelKey: "tools.rnode_flasher.detect_rnode", danger: false },
        { id: "diagnose", icon: "stethoscope", labelKey: "tools.rnode_flasher.run_diagnostics", danger: false },
        { id: "reboot", icon: "restart", labelKey: "tools.rnode_flasher.reboot_rnode", danger: false },
        { id: "read-display", icon: "monitor", labelKey: "tools.rnode_flasher.read_display", danger: false },
        { id: "dump-eeprom", icon: "database-export", labelKey: "tools.rnode_flasher.dump_eeprom", danger: false },
        {
            id: "wipe-eeprom",
            icon: "eraser",
            labelKey: "tools.rnode_flasher.wipe_eeprom",
            danger: true,
        },
    ];

    interface Props {
        disabledActions?: string[];
        onaction?: (actionId: string) => void;
    }

    let { disabledActions = [], onaction }: Props = $props();

    let availableActions = $derived(ALL_ACTIONS.filter((a) => !disabledActions.includes(a.id)));
</script>

<div class="space-y-4">
    <div class="text-xs font-bold text-gray-400 dark:text-zinc-600 uppercase tracking-widest">
        {t("tools.rnode_flasher.advanced_tools")}
    </div>
    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
        {#each availableActions as action (action.id)}
            <button
                type="button"
                class="inline-flex items-center justify-center gap-1.5 rounded-xl px-3 py-2.5 text-[11px] font-bold border transition-all active:scale-95 cursor-pointer {action.danger
                    ? 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border-red-100 dark:border-red-900/30 hover:bg-red-100 dark:hover:bg-red-900/40'
                    : 'bg-sem-surface-muted hover:bg-gray-200 dark:hover:bg-sem-surface-muted text-sem-fg-muted border-sem-border'}"
                onclick={() => onaction?.(action.id)}
            >
                <MaterialDesignIcon iconName={action.icon} class="size-4" />
                <span>{t(action.labelKey)}</span>
            </button>
        {/each}
    </div>
</div>
