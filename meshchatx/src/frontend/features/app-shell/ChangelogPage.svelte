<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    /**
     * Route page for /changelog. ChangelogModal renders full page when isPage.
     */
    import ChangelogModal from "./components/ChangelogModal.svelte";
</script>

<div class="flex flex-1 min-h-0 h-full min-w-0 w-full overflow-hidden bg-sem-canvas">
    <ChangelogModal isPage={true} />
</div>
