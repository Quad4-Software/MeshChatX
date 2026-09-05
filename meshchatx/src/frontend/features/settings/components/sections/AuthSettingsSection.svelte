<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Toggle from "../Toggle.svelte";

    interface Props {
        visible?: boolean;
        config?: Record<string, any>;
        onauthenabledchange?: (val: boolean) => void;
    }

    let { visible = true, config = {}, onauthenabledchange }: Props = $props();
</script>

{#if visible}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">Security</div>
                <h2>Authentication</h2>
                <p>Require a password to access the web interface.</p>
            </div>
        </header>
        <div class="settings-section__body space-y-3">
            <label class="setting-toggle">
                <Toggle id="auth-enabled" checked={Boolean(config.auth_enabled)} onchange={onauthenabledchange} />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">Enable Authentication</span>
                    <span class="setting-toggle__description">Protect your instance with a password.</span>
                </span>
            </label>
            {#if config.auth_enabled}
                <div class="info-callout">
                    <p class="text-sm">
                        Authentication is currently enabled. You will be asked for your password when accessing the web
                        interface.
                    </p>
                </div>
            {/if}
        </div>
    </section>
{/if}
