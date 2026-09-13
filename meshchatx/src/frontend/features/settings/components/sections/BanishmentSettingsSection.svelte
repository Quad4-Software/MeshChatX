<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import SettingsSectionBlock from "../SettingsSectionBlock.svelte";
    import SettingToggleRow from "../SettingToggleRow.svelte";
    import { t } from "../../../../js/i18n.js";

    interface Props {
        visible?: boolean;
        config?: Record<string, any>;
        onenabledchange?: (val: boolean) => void;
        ontextchange?: (val: string) => void;
        oncolorchange?: (val: string) => void;
    }

    let { visible = true, config = {}, onenabledchange, ontextchange, oncolorchange }: Props = $props();
</script>

<SettingsSectionBlock
    show={visible}
    eyebrow={t("app.privacy_eyebrow")}
    title={t("app.banishment")}
    description={t("app.banishment_description")}
    bodyClass="space-y-4"
>
    <SettingToggleRow
        id="banished-effect-enabled"
        checked={Boolean(config.banished_effect_enabled)}
        title={t("app.banished_effect_enabled")}
        description={t("app.banished_effect_description")}
        onchange={onenabledchange}
    />

    {#if config.banished_effect_enabled}
        <div class="space-y-4">
            <div class="space-y-2">
                <label for="banished-text-input" class="text-sm font-medium text-sem-fg block">
                    {t("app.banished_text_label")}
                </label>
                <input
                    id="banished-text-input"
                    value={config.banished_text}
                    type="text"
                    class="input-field"
                    oninput={(e) => ontextchange?.((e.target as HTMLInputElement).value)}
                />
                <div class="text-xs text-sem-fg-muted">
                    {t("app.banished_text_description")}
                </div>
            </div>

            <div class="space-y-2">
                <label for="banished-color-input" class="text-sm font-medium text-sem-fg block">
                    {t("app.banished_color_label")}
                </label>
                <div class="flex gap-2">
                    <input
                        value={config.banished_color}
                        type="color"
                        class="color-fill-input w-12 h-10 rounded-xl border border-sem-border cursor-pointer"
                        oninput={(e) => oncolorchange?.((e.target as HTMLInputElement).value)}
                    />
                    <input
                        id="banished-color-input"
                        value={config.banished_color}
                        type="text"
                        class="input-field monospace-field"
                        oninput={(e) => oncolorchange?.((e.target as HTMLInputElement).value)}
                    />
                </div>
                <div class="text-xs text-sem-fg-muted">
                    {t("app.banished_color_description")}
                </div>
            </div>
        </div>
    {/if}
</SettingsSectionBlock>
