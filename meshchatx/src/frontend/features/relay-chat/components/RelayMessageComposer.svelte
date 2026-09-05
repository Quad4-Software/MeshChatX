<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import type { RrcMember } from "../lib/types.js";

    interface Props {
        disabled?: boolean;
        placeholder?: string;
        members?: RrcMember[];
        onsend?: (text: string) => void;
    }

    let { disabled = false, placeholder = "", members: _members = [], onsend }: Props = $props();

    let text = $state("");
    let textareaEl = $state<HTMLTextAreaElement | null>(null);

    function handleSubmit() {
        const clean = text.trim();
        if (!clean || disabled) return;
        onsend?.(clean);
        text = "";
        if (textareaEl) {
            textareaEl.style.height = "auto";
        }
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    }

    function handleInput() {
        if (!textareaEl) return;
        textareaEl.style.height = "auto";
        textareaEl.style.height = `${Math.min(textareaEl.scrollHeight, 120)}px`;
    }
</script>

<div class="border-t border-sem-border bg-sem-surface p-2 sm:p-3">
    <div class="flex items-end gap-2">
        <div class="flex-1 min-w-0 relative">
            <textarea
                bind:this={textareaEl}
                bind:value={text}
                rows={1}
                {disabled}
                placeholder={placeholder || t("relay_chat.composer_placeholder")}
                class="w-full resize-none rounded-xl border border-sem-border bg-sem-canvas px-3 py-2 text-sm text-sem-fg placeholder-sem-fg-muted focus:outline-hidden focus:border-sem-accent min-h-[38px] max-h-[120px]"
                onkeydown={handleKeydown}
                oninput={handleInput}></textarea>
        </div>

        <button
            type="button"
            class="inline-flex h-[38px] items-center justify-center rounded-xl bg-sem-action-primary px-4 text-sm font-semibold text-white transition hover:bg-sem-action-primary-hover disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
            disabled={disabled || !text.trim()}
            onclick={handleSubmit}
        >
            <MaterialDesignIcon iconName="send" class="size-4" />
        </button>
    </div>
</div>
