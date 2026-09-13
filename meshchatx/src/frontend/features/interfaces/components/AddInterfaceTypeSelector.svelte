<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { TRANSPORT_TYPE_OPTIONS } from "../lib/constants.js";

    interface Props {
        name: string;
        type: string | null;
        isEditing?: boolean;
        onnamechange?: (name: string) => void;
        ontypechange?: (type: string | null) => void;
    }

    let { name = "", type = null, isEditing = false, onnamechange, ontypechange }: Props = $props();
</script>

<div class="space-y-6">
    <div class="flex items-center gap-2 pb-2 border-b border-sem-border">
        <MaterialDesignIcon iconName="information-outline" class="w-5 h-5 text-gray-400" />
        <h3 class="font-bold text-sem-fg">Basic Configuration</h3>
    </div>

    <div>
        <label for="iface-name-input" class="glass-label block font-medium mb-1"> Interface Name </label>
        <input
            id="iface-name-input"
            value={name}
            type="text"
            disabled={isEditing}
            placeholder="e.g. Home Node or Mobile TCP"
            class="input-field {isEditing ? 'cursor-not-allowed opacity-60' : ''}"
            oninput={(e) => onnamechange?.((e.target as HTMLInputElement).value)}
        />
    </div>

    <div>
        <label for="iface-more-options-select" class="glass-label block font-medium mb-1"> Transport Type </label>

        <!-- Visual Transport Selection -->
        <div class="grid grid-cols-2 gap-2">
            {#each TRANSPORT_TYPE_OPTIONS as opt (opt.id)}
                <button
                    type="button"
                    class="flex flex-col items-center justify-center p-3 rounded-2xl border transition-all duration-200 text-center gap-1 group {type ===
                    opt.id
                        ? 'bg-blue-500/10 border-blue-500 ring-1 ring-blue-500/50'
                        : 'bg-gray-50/50 dark:bg-zinc-800/30 border-sem-border hover:border-gray-300 dark:hover:border-zinc-600'}"
                    onclick={() => ontypechange?.(opt.id)}
                >
                    <MaterialDesignIcon
                        iconName={opt.icon}
                        class="w-6 h-6 transition-transform group-hover:scale-110 {type === opt.id
                            ? 'text-blue-500'
                            : opt.color}"
                    />
                    <span
                        class="text-[10px] font-bold uppercase tracking-tight {type === opt.id
                            ? 'text-blue-700 dark:text-blue-400'
                            : 'text-sem-fg-muted'}"
                    >
                        {opt.name}
                    </span>
                </button>
            {/each}
        </div>

        <!-- Fallback/More select for less common types -->
        <div class="mt-3">
            <select
                id="iface-more-options-select"
                value={type || ""}
                class="input-field appearance-none pr-10 py-1.5! text-[11px]! opacity-70 hover:opacity-100"
                onchange={(e) => ontypechange?.((e.target as HTMLSelectElement).value || null)}
            >
                <option value="">More options...</option>
                <option value="AX25KISSInterface">AX.25 KISS (Amateur Radio)</option>
                <option value="LocalInterface">Local Interface (Loopback)</option>
                <option value="PipeInterface">Pipe Interface (External)</option>
                <option value="RNodeIPInterface">RNode over IP</option>
                <option value="BackboneInterface">Backbone (public relay)</option>
                <option value="__external__">Custom / external module (RNS interfacepath)</option>
            </select>
        </div>
    </div>
</div>
