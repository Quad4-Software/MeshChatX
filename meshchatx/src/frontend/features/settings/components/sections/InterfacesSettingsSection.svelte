<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Toggle from "../Toggle.svelte";
    import { t } from "../../../../js/i18n.js";

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
                <div class="settings-section__eyebrow">Adapters</div>
                <h2>{t("app.interfaces")}</h2>
                <p>Show curated community configs inside the interface wizard.</p>
            </div>
        </header>
        <div class="settings-section__body space-y-3">
            <label class="setting-toggle">
                <Toggle
                    id="show-community-interfaces"
                    checked={Boolean(config.show_suggested_community_interfaces)}
                    onchange={(val) => onupdatefield?.({ key: "show_suggested_community_interfaces", value: val })}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("app.show_community_interfaces")}</span>
                    <span class="setting-toggle__description">{t("app.community_interfaces_description")}</span>
                </span>
            </label>
        </div>
    </section>
{/if}
