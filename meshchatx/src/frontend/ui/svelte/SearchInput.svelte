<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script lang="ts">
    import type { HTMLInputAttributes } from "svelte/elements";
    import MaterialDesignIcon from "./MaterialDesignIcon.svelte";
    import { t } from "../../js/i18n.js";

    interface Props extends Omit<HTMLInputAttributes, "value"> {
        value?: string;
        placeholder?: string;
        icon?: string;
        compact?: boolean;
        clearTitle?: string;
        loading?: boolean;
        onclear?: () => void;
    }

    let {
        value = $bindable(""),
        placeholder = "",
        icon = "magnify",
        compact = false,
        clearTitle = "",
        loading = false,
        onclear,
        ...rest
    }: Props = $props();

    function clear(): void {
        value = "";
        onclear?.();
    }
</script>

<div class="relative group">
    <MaterialDesignIcon
        iconName={icon}
        class="absolute left-3 top-1/2 -translate-y-1/2 shrink-0 text-gray-400 group-focus-within:text-sem-accent transition-colors pointer-events-none z-10 {compact
            ? 'size-4'
            : 'size-5'}"
    />
    <input
        bind:value
        type="text"
        {placeholder}
        class={compact ? "search-input search-input-compact" : "search-input"}
        onkeydown={(e) => {
            if (e.key === "Escape") {
                clear();
            }
        }}
        {...rest}
    />
    {#if loading}
        <div class="absolute right-3 top-1/2 -translate-y-1/2 flex items-center">
            <MaterialDesignIcon
                iconName="loading"
                class="{compact ? 'size-3.5' : 'size-4'} text-gray-400 animate-spin"
            />
        </div>
    {:else if value}
        <button
            type="button"
            class="absolute right-2.5 top-1/2 -translate-y-1/2 flex items-center text-sem-fg-muted hover:text-sem-fg focus-ring-sem rounded-full p-0.5 transition-colors"
            title={clearTitle || t("common.clear")}
            onclick={clear}
        >
            <MaterialDesignIcon iconName="close-circle" class={compact ? "size-4" : "size-5"} />
        </button>
    {/if}
</div>
