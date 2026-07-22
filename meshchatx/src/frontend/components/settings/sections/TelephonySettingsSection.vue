<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <SettingsSectionBlock
        v-show="visible"
        eyebrow="Telephony"
        title="Telephone (LXST)"
        description="Enable or disable the integrated voice calling system."
        body-class="space-y-4"
    >
        <SettingToggleRow
            id="telephone-enabled-toggle"
            :model-value="config.telephone_enabled"
            title="Enable Telephone (LXST)"
            description="Allow incoming and outgoing voice calls over the mesh network."
            hint="Disabling will end any active calls."
            @update:model-value="$emit('enabled-change', $event)"
        />
    </SettingsSectionBlock>
</template>

<script>
import SettingsSectionBlock from "../SettingsSectionBlock.vue";
import SettingToggleRow from "../SettingToggleRow.vue";

export default {
    name: "TelephonySettingsSection",
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
    emits: ["enabled-change"],
};
</script>
