<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "./MaterialDesignIcon.svelte";

    interface Props {
        message?: string;
        class?: string;
    }

    let { message = "", class: rootClass = "" }: Props = $props();
</script>

<div class="flex flex-col items-center justify-center px-4 py-10 text-center {rootClass}">
    <MaterialDesignIcon iconName="loading" class="size-8 animate-spin text-sem-accent motion-reduce:animate-none" />
    {#if message}
        <p class="mt-3 text-sm text-sem-fg-muted">{message}</p>
    {/if}
</div>
