<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";

    let {
        destinationHash = $bindable(""),
        title = $bindable(""),
        content = $bindable(""),
        isGenerating = false,
        canGenerate = false,
        ongenerate,
    }: {
        destinationHash: string;
        title: string;
        content: string;
        isGenerating?: boolean;
        canGenerate?: boolean;
        ongenerate?: () => void;
    } = $props();
</script>

<section class="rounded-lg border border-sem-border overflow-hidden bg-sem-surface">
    <div class="px-4 py-3 border-b border-sem-border bg-gray-50/80 dark:bg-zinc-900/50">
        <h2 class="flex items-center gap-2 text-base font-semibold text-sem-fg">
            <MaterialDesignIcon iconName="pencil-outline" class="size-5 text-gray-400 shrink-0" />
            Compose Message
        </h2>
    </div>
    <div class="px-4 py-4 space-y-3 text-gray-900 dark:text-gray-100">
        <div>
            <label
                class="block text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest mb-1.5"
                for="paper-destination-hash"
            >
                Recipient Address
            </label>
            <input
                id="paper-destination-hash"
                bind:value={destinationHash}
                type="text"
                placeholder="Destination hash (e.g. a39610...)"
                class="input-field font-mono text-sm"
                maxlength="32"
            />
        </div>
        <div>
            <label
                class="block text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest mb-1.5"
                for="paper-subject"
            >
                Subject (Optional)
            </label>
            <input
                id="paper-subject"
                bind:value={title}
                type="text"
                placeholder="Message title..."
                class="input-field text-sm"
            />
        </div>
        <div>
            <label
                class="block text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest mb-1.5"
                for="paper-content"
            >
                Message Content
            </label>
            <textarea
                id="paper-content"
                bind:value={content}
                rows="4"
                placeholder="Type your message here..."
                class="input-field resize-none text-sm"
            ></textarea>
        </div>
        <button
            type="button"
            class="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold shadow-lg shadow-blue-500/20 transition-all active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none text-sm"
            disabled={!canGenerate || isGenerating}
            onclick={() => ongenerate?.()}
        >
            {#if isGenerating}
                <div class="size-4 border-2 border-white/20 border-t-white rounded-full animate-spin"></div>
                Generating...
            {:else}
                <MaterialDesignIcon iconName="qrcode-plus" class="size-5" />
                Generate Paper Message
            {/if}
        </button>
    </div>
</section>
