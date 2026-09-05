<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import SettingsSectionBlock from "../SettingsSectionBlock.svelte";
    import SettingToggleRow from "../SettingToggleRow.svelte";

    interface Props {
        visible?: boolean;
        config?: Record<string, any>;
        onenabledchange?: (val: boolean) => void;
    }

    let { visible = true, config = {}, onenabledchange }: Props = $props();
</script>

<SettingsSectionBlock
    show={visible}
    eyebrow="Telephony"
    title="Telephone (LXST)"
    description="Enable or disable the integrated voice calling system."
    bodyClass="space-y-4"
>
    <SettingToggleRow
        id="telephone-enabled-toggle"
        checked={Boolean(config.telephone_enabled)}
        title="Enable Telephone (LXST)"
        description="Allow incoming and outgoing voice calls over the mesh network."
        hint="Disabling will end any active calls."
        onchange={onenabledchange}
    />
</SettingsSectionBlock>
