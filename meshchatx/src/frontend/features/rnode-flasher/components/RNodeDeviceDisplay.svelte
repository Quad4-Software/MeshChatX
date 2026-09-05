<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";

    interface Props {
        image?: string | null;
        onclear?: () => void;
    }

    let { image = null, onclear }: Props = $props();
</script>

{#if image}
    <div class="p-4 rounded-2xl bg-zinc-950 flex flex-col items-center gap-2 border border-zinc-800">
        <img src={image} alt="RNode display" class="h-24 sm:h-28 pixelated" />
        <button
            type="button"
            class="text-[10px] font-bold uppercase tracking-wider text-zinc-400 hover:text-zinc-200 cursor-pointer"
            onclick={() => onclear?.()}
        >
            {t("common.clear")}
        </button>
    </div>
{/if}

<style>
    .pixelated {
        image-rendering: pixelated;
    }
</style>
