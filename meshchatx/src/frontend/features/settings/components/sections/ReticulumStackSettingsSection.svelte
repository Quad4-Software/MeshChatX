<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../../js/i18n.js";

    interface Props {
        visible?: boolean;
        reloadingRns?: boolean;
        reloadRnsStatusMessage?: string;
        onreloadrns?: () => void;
    }

    let { visible = true, reloadingRns = false, reloadRnsStatusMessage = "", onreloadrns }: Props = $props();
</script>

{#if visible}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">{t("app.system")}</div>
                <h2>{t("app.reticulum_stack")}</h2>
                <p>{t("app.reticulum_stack_description")}</p>
            </div>
        </header>
        <div class="settings-section__body space-y-4">
            <div class="grid grid-cols-1 gap-3">
                <button
                    type="button"
                    class="btn-maintenance border-violet-200 dark:border-violet-900/30 text-violet-800 dark:text-violet-200 bg-violet-50 dark:bg-violet-900/10 hover:bg-violet-100 dark:hover:bg-violet-900/20 disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:bg-violet-50 dark:disabled:hover:bg-violet-900/10 cursor-pointer"
                    disabled={reloadingRns}
                    onclick={onreloadrns}
                >
                    <div class="flex flex-col items-start text-left">
                        <div class="font-bold flex items-center gap-2">
                            <MaterialDesignIcon iconName="restart" class="size-4" />
                            {t("app.reload_rns")}
                        </div>
                    </div>
                </button>
                {#if reloadRnsStatusMessage}
                    <p class="text-xs {reloadingRns ? 'text-sem-accent' : 'text-sem-fg-muted'}">
                        {reloadRnsStatusMessage}
                    </p>
                {/if}
            </div>
        </div>
    </section>
{/if}
