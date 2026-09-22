<!-- SPDX-License-Identifier: 0BSD -->
<script>
    import Toggle from "../../../meshchatx/src/frontend/ui/svelte/Toggle.svelte";

    let { onchange } = $props();
    let checked = $state(false);
</script>

<Toggle id="browser-toggle" bind:checked label="Browser toggle" {onchange} />
