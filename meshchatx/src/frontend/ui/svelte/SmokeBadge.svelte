<!-- SPDX-License-Identifier: 0BSD -->

<script>
    /**
     * Pipeline smoke component. Not routed. Proves Svelte 5 compile + test.
     * @type {{ label?: string }}
     */
    let { label = "ok" } = $props();
</script>

<span data-testid="svelte-smoke-badge" class="inline-flex items-center rounded px-2 py-0.5 text-xs">{label}</span>
