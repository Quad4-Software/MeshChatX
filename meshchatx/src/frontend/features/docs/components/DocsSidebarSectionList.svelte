<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import type { DocSection } from "../lib/types.js";

    interface Props {
        visibleDocSections: DocSection[];
        selectedDocPath: string | null;
        onSelectDoc: (path: string) => void;
    }

    let { visibleDocSections, selectedDocPath, onSelectDoc }: Props = $props();
</script>

<nav class="flex-1 overflow-y-auto p-3 space-y-5 custom-scroll">
    {#each visibleDocSections as section (section.id)}
        <div>
            <p class="px-2 mb-2 text-[10px] font-bold uppercase tracking-widest text-sem-fg-muted">
                {section.title}
            </p>
            <div class="space-y-0.5">
                {#each section.items as item (item.path)}
                    <button
                        type="button"
                        class="w-full text-left px-3 py-2 rounded-xl text-xs transition-all flex items-center gap-2.5 {selectedDocPath ===
                        item.path
                            ? 'bg-cyan-50 dark:bg-cyan-950/40 text-cyan-700 dark:text-cyan-300 font-semibold shadow-xs ring-1 ring-cyan-200/80 dark:ring-cyan-800/60'
                            : 'text-sem-fg-muted hover:bg-sem-surface-muted hover:text-sem-fg'}"
                        onclick={() => onSelectDoc(item.path)}
                    >
                        <MaterialDesignIcon
                            iconName={item.type === "markdown" ? "language-markdown" : "file-document-outline"}
                            class="w-4 h-4 shrink-0 opacity-70"
                        />
                        <span class="truncate">{item.title}</span>
                    </button>
                {/each}
            </div>
        </div>
    {/each}
</nav>
