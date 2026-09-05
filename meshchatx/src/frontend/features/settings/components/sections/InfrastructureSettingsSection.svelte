<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    interface Props {
        visible?: boolean;
        config?: Record<string, any>;
        onupdatefield?: (data: { key: string; value: any }) => void;
    }

    let { visible = true, config = {}, onupdatefield }: Props = $props();
</script>

{#if visible}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">Infrastructure</div>
                <h2>Sources & Mirroring</h2>
                <p>Customize URLs for documentation and external resources.</p>
            </div>
        </header>
        <div class="settings-section__body space-y-4">
            <div class="space-y-2">
                <label for="gitea-base-url-input" class="text-sm font-medium text-sem-fg block"> Gitea Base URL </label>
                <input
                    id="gitea-base-url-input"
                    value={config.gitea_base_url || ""}
                    type="text"
                    placeholder="https://github.com/example-org"
                    class="input-field"
                    oninput={(e) =>
                        onupdatefield?.({ key: "gitea_base_url", value: (e.target as HTMLInputElement).value })}
                />
                <div class="text-xs text-sem-fg-muted">The base URL for your preferred Gitea instance.</div>
            </div>
        </div>
    </section>
{/if}
