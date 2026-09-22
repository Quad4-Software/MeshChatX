<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import type { RrcMember } from "../lib/types.js";

    interface Props {
        text?: string;
        disabled?: boolean;
        maxlength?: number;
        members?: RrcMember[];
        onkeydown?: (e: KeyboardEvent) => void;
        onsend?: () => void;
    }

    let {
        text = $bindable(""),
        disabled = false,
        maxlength = 350,
        members: _members = [],
        onkeydown,
        onsend,
    }: Props = $props();

    let inputEl = $state<HTMLInputElement | null>(null);

    export function focus() {
        inputEl?.focus();
    }
</script>

<form
    class="flex items-center gap-2 p-2.5 border-t border-sem-border bg-sem-canvas shrink-0"
    onsubmit={(e) => {
        e.preventDefault();
        onsend?.();
    }}
>
    <input
        bind:this={inputEl}
        bind:value={text}
        type="text"
        {maxlength}
        {disabled}
        placeholder={t("relay_chat.message_placeholder")}
        class="input-field"
        onkeydown={(e) => onkeydown?.(e)}
    />
    <button
        type="submit"
        class="inline-flex items-center justify-center gap-1.5 rounded-lg bg-sem-action-primary px-3 py-2 text-sm font-semibold text-sem-action-primary-text transition hover:bg-sem-action-primary-hover disabled:opacity-50 disabled:cursor-not-allowed shrink-0 p-2.5!"
        title={t("relay_chat.send")}
        disabled={!text.trim() || disabled}
    >
        <MaterialDesignIcon iconName="send" class="size-5" />
    </button>
</form>
