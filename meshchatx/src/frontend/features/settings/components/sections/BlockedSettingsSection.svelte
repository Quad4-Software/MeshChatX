<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    interface Props {
        visible?: boolean;
    }

    let { visible = true }: Props = $props();
</script>

{#if visible}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">Privacy</div>
                <h2>Banished</h2>
                <p>Manage Banished users and nodes</p>
            </div>
            <a href="#/blocked" class="primary-chip">Manage Banished</a>
        </header>
        <div class="settings-section__body">
            <p class="text-sm text-sem-fg-muted">
                Banished users and nodes will not be able to send you messages, and their announces will be ignored.
            </p>
        </div>
    </section>
{/if}
