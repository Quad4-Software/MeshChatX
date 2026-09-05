<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    /**
     * Route page for /tutorial. Opens the tutorial immediately, matching the
     * vue-router record that used TutorialModal with meta.isPage.
     */
    import TutorialModalHost from "./components/TutorialModalHost.svelte";
</script>

<div class="flex flex-1 min-h-0 h-full min-w-0 w-full overflow-hidden bg-sem-canvas">
    <TutorialModalHost isPage={true} openOnMount={true} />
</div>
