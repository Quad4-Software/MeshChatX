<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Toggle from "./Toggle.svelte";
    import BundledDocsHint from "./BundledDocsHint.svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import type { DiscoveryConfig } from "../lib/types.js";

    interface Props {
        discoveryConfig: DiscoveryConfig;
        savingDiscoveryConfig?: boolean;
        onsave?: () => void;
    }

    let { discoveryConfig = $bindable(), savingDiscoveryConfig = false, onsave }: Props = $props();
</script>

<div class="p-4 rounded-2xl bg-gray-50 dark:bg-zinc-800/60 border border-gray-200 dark:border-zinc-700 space-y-4">
    <div class="text-sm font-semibold text-sem-fg">Automatic Interface Discovery</div>
    <div class="text-xs text-sem-fg-muted">
        MeshChatX can automatically discover and connect to interfaces announced over the mesh.
    </div>

    <div class="space-y-3">
        <label
            for="autodiscover-allow-all"
            class="flex items-center justify-between text-xs text-gray-700 dark:text-gray-300 cursor-pointer"
        >
            <span>Allow all discovered interfaces</span>
            <Toggle id="autodiscover-allow-all" bind:checked={discoveryConfig.autodiscover_allow_all} />
        </label>

        <div>
            <label
                for="autodiscover-list-input"
                class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
                Allowlist (comma-separated IDs/hosts)
            </label>
            <input
                id="autodiscover-list-input"
                type="text"
                bind:value={discoveryConfig.autodiscover_list}
                placeholder="tc1, tc2..."
                class="w-full text-xs rounded-xl border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sem-fg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
        </div>

        <div>
            <label
                for="autodiscover-blacklist-input"
                class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
                Blacklist (comma-separated IDs/hosts)
            </label>
            <input
                id="autodiscover-blacklist-input"
                type="text"
                bind:value={discoveryConfig.autodiscover_blacklist}
                placeholder="tc3, tc4..."
                class="w-full text-xs rounded-xl border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sem-fg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
        </div>

        <div>
            <label
                for="autodiscover-bootstrap-only"
                class="flex items-center justify-between text-xs text-gray-700 dark:text-gray-300 cursor-pointer"
            >
                <span>{t("interfaces.discovery_default_bootstrap_only")}</span>
                <Toggle
                    id="autodiscover-bootstrap-only"
                    bind:checked={discoveryConfig.autodiscover_default_bootstrap_only}
                />
            </label>
            <BundledDocsHint />
        </div>
    </div>

    <div class="flex justify-end pt-2">
        <button
            type="button"
            class="primary-btn text-xs px-3 py-1.5 flex items-center gap-1.5"
            disabled={savingDiscoveryConfig}
            onclick={onsave}
        >
            {#if savingDiscoveryConfig}
                <MaterialDesignIcon iconName="loading" class="w-3.5 h-3.5 animate-spin" />
            {/if}
            <span>Save Settings</span>
        </button>
    </div>
</div>
