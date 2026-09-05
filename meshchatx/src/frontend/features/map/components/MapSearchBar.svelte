<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    interface SearchResult {
        display_name: string;
        type?: string;
        [key: string]: unknown;
    }

    interface Props {
        modelValue?: string;
        query?: string;
        results?: SearchResult[];
        searchResults?: SearchResult[];
        error?: string | null;
        searching?: boolean;
        isSearching?: boolean;
        showResults?: boolean;
        isFocused?: boolean;
        placeholder?: string;
        onsearch?: () => void;
        onclear?: () => void;
        onfocus?: () => void;
        onselect?: (result: SearchResult) => void;
        oninput?: (e: Event) => void;
    }

    let {
        modelValue = $bindable(""),
        query = $bindable(""),
        results = [],
        searchResults = [],
        error = null,
        searching = false,
        isSearching = false,
        showResults = false,
        isFocused = $bindable(false),
        placeholder = "",
        onsearch,
        onclear,
        onfocus,
        onselect,
        oninput,
    }: Props = $props();

    let inputEl = $state<HTMLInputElement | null>(null);

    let activeQuery = $derived(query || modelValue);
    let activeResults = $derived(searchResults.length > 0 ? searchResults : results);
    let activeSearching = $derived(searching || isSearching);

    export function focus() {
        inputEl?.focus?.();
    }

    function handleInput(e: Event) {
        const target = e.target as HTMLInputElement;
        modelValue = target.value;
        query = target.value;
        oninput?.(e);
    }

    function handleClear() {
        modelValue = "";
        query = "";
        onclear?.();
    }
</script>

<div class="relative w-full">
    <div class="flex items-center bg-sem-surface rounded-xl shadow-2xl border border-sem-border ring-0">
        <input
            bind:this={inputEl}
            value={activeQuery}
            type="text"
            class="flex-1 px-4 py-2.5 bg-transparent text-sem-fg placeholder-gray-400 focus:outline-hidden focus:ring-0 border-0 text-sm"
            placeholder={placeholder || t("map.search_placeholder")}
            oninput={handleInput}
            onkeydown={(e) => {
                if (e.key === "Enter") onsearch?.();
            }}
            onfocus={() => {
                isFocused = true;
                onfocus?.();
            }}
            onblur={() => {
                isFocused = false;
            }}
        />
        {#if activeQuery}
            <button
                type="button"
                class="p-2 text-sem-fg-muted hover:text-sem-fg transition-colors cursor-pointer"
                onclick={handleClear}
            >
                <MaterialDesignIcon iconName="close" class="size-[18px]" />
            </button>
        {/if}
        <button
            type="button"
            class="p-2 mr-1 text-blue-500 hover:text-blue-600 disabled:text-gray-300 transition-colors cursor-pointer"
            disabled={!activeQuery || activeSearching}
            onclick={() => onsearch?.()}
        >
            <MaterialDesignIcon
                iconName={activeSearching ? "loading" : "magnify"}
                class="size-5 {activeSearching ? 'animate-spin' : ''}"
            />
        </button>
    </div>

    {#if showResults && activeResults.length > 0}
        <div
            class="absolute top-full left-0 right-0 mt-1 max-h-60 overflow-y-auto bg-sem-surface rounded-xl shadow-2xl border border-sem-border z-50 text-sm"
        >
            {#each activeResults as result, idx (idx)}
                <button
                    type="button"
                    class="w-full text-left px-4 py-2.5 hover:bg-sem-surface-muted transition-colors border-b border-sem-border last:border-b-0 cursor-pointer text-sem-fg"
                    onclick={() => onselect?.(result)}
                >
                    <div class="font-medium truncate">{result.display_name}</div>
                    {#if result.type}
                        <div class="text-xs text-sem-fg-muted capitalize">{result.type}</div>
                    {/if}
                </button>
            {/each}
        </div>
    {/if}

    {#if error}
        <div
            class="absolute top-full left-0 right-0 mt-1 p-2 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-xs rounded-lg"
        >
            {error}
        </div>
    {/if}
</div>
