<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script lang="ts" module>
    export interface LxmfIconDraft {
        icon_name: string;
        fg_color: string;
        bg_color: string;
    }

    export const LXMF_ICON_DEFAULT_FG = "#6b7280";
    export const LXMF_ICON_DEFAULT_BG = "#e5e7eb";

    export function defaultBotIconDraft(iconName = "robot"): LxmfIconDraft {
        return {
            icon_name: iconName,
            fg_color: LXMF_ICON_DEFAULT_FG,
            bg_color: LXMF_ICON_DEFAULT_BG,
        };
    }
</script>

<script lang="ts">
    import ColourPickerDropdown from "./ColourPickerDropdown.svelte";
    import LxmfUserIcon from "./LxmfUserIcon.svelte";
    import SearchInput from "./SearchInput.svelte";
    import { buildMdiIconNames } from "../../js/mdiIconNames.js";
    import { t } from "../../js/i18n.js";

    interface Props {
        value?: LxmfIconDraft | null;
    }

    let { value = $bindable(null) }: Props = $props();

    let search = $state("");
    const maxSearchResults = 200;
    const iconNames = buildMdiIconNames();

    const draft = $derived<LxmfIconDraft>({
        icon_name: value?.icon_name ? value.icon_name : "",
        fg_color: value?.fg_color ? value.fg_color : LXMF_ICON_DEFAULT_FG,
        bg_color: value?.bg_color ? value.bg_color : LXMF_ICON_DEFAULT_BG,
    });

    const draftKey = $derived(`${draft.icon_name}|${draft.fg_color}|${draft.bg_color}`);

    const searchedIconNames = $derived.by(() => {
        const q = search.toLowerCase();
        return iconNames.filter((name) => name.toLowerCase().includes(q)).slice(0, maxSearchResults);
    });

    function emit(patch: Partial<LxmfIconDraft>): void {
        const next = { ...draft, ...patch };
        if (!next.icon_name) {
            value = null;
            return;
        }
        value = next;
    }

    function selectIcon(name: string): void {
        emit({ icon_name: name });
    }

    function setFg(val: string): void {
        emit({ fg_color: String(val || "").trim() });
    }

    function setBg(val: string): void {
        emit({ bg_color: String(val || "").trim() });
    }

    function clear(): void {
        value = null;
    }
</script>

<div class="space-y-4">
    <div class="flex items-center gap-4">
        <div class="p-4 bg-gray-50 dark:bg-zinc-800 rounded-xl shrink-0">
            {#key draftKey}
                <LxmfUserIcon
                    iconName={draft.icon_name}
                    iconForegroundColour={draft.fg_color}
                    iconBackgroundColour={draft.bg_color}
                    iconClass="size-14"
                />
            {/key}
        </div>
        <div class="flex-1 space-y-3 min-w-0">
            <div class="flex items-center justify-between gap-3">
                <span class="text-sm font-medium text-sem-fg-muted">{t("bots.icon_background")}</span>
                <div class="flex items-center gap-2">
                    <ColourPickerDropdown colour={draft.bg_color} onchange={(c) => setBg(c)} />
                    <input
                        value={draft.bg_color}
                        type="text"
                        class="w-24 px-2 py-1.5 text-xs border border-gray-300 dark:border-zinc-700 rounded-lg bg-white dark:bg-zinc-800 text-sem-fg font-mono"
                        placeholder="#e5e7eb"
                        oninput={(e) => setBg((e.target as HTMLInputElement).value)}
                    />
                </div>
            </div>
            <div class="flex items-center justify-between gap-3">
                <span class="text-sm font-medium text-sem-fg-muted">{t("bots.icon_foreground")}</span>
                <div class="flex items-center gap-2">
                    <ColourPickerDropdown colour={draft.fg_color} onchange={(c) => setFg(c)} />
                    <input
                        value={draft.fg_color}
                        type="text"
                        class="w-24 px-2 py-1.5 text-xs border border-gray-300 dark:border-zinc-700 rounded-lg bg-white dark:bg-zinc-800 text-sem-fg font-mono"
                        placeholder="#6b7280"
                        oninput={(e) => setFg((e.target as HTMLInputElement).value)}
                    />
                </div>
            </div>
        </div>
    </div>

    <SearchInput bind:value={search} placeholder={t("bots.icon_search", { count: iconNames.length })} />
    <div class="grid grid-cols-3 sm:grid-cols-4 gap-2 max-h-56 overflow-y-auto p-1 rounded-lg border border-sem-border">
        {#each searchedIconNames as name (name)}
            <button
                type="button"
                class="flex flex-col items-center justify-center p-2.5 rounded-lg border-2 transition-all hover:bg-sem-surface-muted hover:border-blue-500 dark:hover:border-blue-500 {draft.icon_name ===
                name
                    ? 'border-blue-500 bg-sem-surface-muted'
                    : 'border-sem-border'}"
                title={name}
                onclick={() => selectIcon(name)}
            >
                <LxmfUserIcon
                    iconName={name}
                    iconForegroundColour={draft.icon_name === name ? draft.fg_color : "#6b7280"}
                    iconBackgroundColour={draft.icon_name === name ? draft.bg_color : "#e5e7eb"}
                    iconClass="size-8"
                />
                <div class="mt-1.5 text-[10px] text-center text-sem-fg-muted truncate w-full">
                    {name}
                </div>
            </button>
        {/each}
    </div>
    {#if searchedIconNames.length === 0}
        <div class="text-center py-4 text-sm text-sem-fg-muted">
            {t("bots.icon_search_empty")}
        </div>
    {/if}

    <div class="flex items-center justify-between gap-2">
        <span class="text-xs text-sem-fg-muted">{t("bots.icon_hint")}</span>
        {#if value}
            <button type="button" class="text-xs text-red-600 dark:text-red-400 hover:underline" onclick={clear}>
                {t("bots.icon_remove")}
            </button>
        {/if}
    </div>
</div>
