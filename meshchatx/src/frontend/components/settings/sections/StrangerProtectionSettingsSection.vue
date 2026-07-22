<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <SettingsSectionBlock
        v-show="visible"
        eyebrow="Security"
        :title="$t('app.stranger_protection')"
        :description="$t('app.stranger_protection_description')"
        body-class="space-y-4"
    >
        <SettingToggleRow
            id="block-attachments-from-strangers"
            :model-value="config.block_attachments_from_strangers"
            :title="$t('app.block_stranger_attachments')"
            :description="$t('app.block_stranger_attachments_description')"
            @update:model-value="$emit('block-attachments-change', $event)"
        />
        <SettingToggleRow
            id="block-all-from-strangers"
            :model-value="config.block_all_from_strangers"
            :title="$t('app.block_all_from_strangers')"
            :description="$t('app.block_all_from_strangers_description')"
            @update:model-value="$emit('block-all-change', $event)"
        />
        <SettingToggleRow
            id="show-unknown-contact-banner"
            :model-value="config.show_unknown_contact_banner"
            :title="$t('app.show_unknown_contact_banner')"
            :description="$t('app.show_unknown_contact_banner_description')"
            @update:model-value="$emit('unknown-banner-change', $event)"
        />
        <SettingToggleRow
            id="warn-on-stranger-links"
            :model-value="config.warn_on_stranger_links"
            :title="$t('app.warn_on_stranger_links')"
            :description="$t('app.warn_on_stranger_links_description')"
            @update:model-value="$emit('warn-links-change', $event)"
        />
    </SettingsSectionBlock>
</template>

<script>
import SettingsSectionBlock from "../SettingsSectionBlock.vue";
import SettingToggleRow from "../SettingToggleRow.vue";

export default {
    name: "StrangerProtectionSettingsSection",
    components: {
        SettingsSectionBlock,
        SettingToggleRow,
    },
    props: {
        visible: {
            type: Boolean,
            default: true,
        },
        config: {
            type: Object,
            required: true,
        },
    },
    emits: ["block-attachments-change", "block-all-change", "unknown-banner-change", "warn-links-change"],
};
</script>
