<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import SettingsSectionBlock from "../SettingsSectionBlock.svelte";
    import SettingToggleRow from "../SettingToggleRow.svelte";
    import { t } from "../../../../js/i18n.js";

    interface Props {
        visible?: boolean;
        config?: Record<string, any>;
        onblockattachmentschange?: (val: boolean) => void;
        onblockallchange?: (val: boolean) => void;
        onunknownbannerchange?: (val: boolean) => void;
        onwarnlinkschange?: (val: boolean) => void;
    }

    let {
        visible = true,
        config = {},
        onblockattachmentschange,
        onblockallchange,
        onunknownbannerchange,
        onwarnlinkschange,
    }: Props = $props();
</script>

<SettingsSectionBlock
    show={visible}
    eyebrow="Security"
    title={t("app.stranger_protection")}
    description={t("app.stranger_protection_description")}
    bodyClass="space-y-4"
>
    <SettingToggleRow
        id="block-attachments-from-strangers"
        checked={Boolean(config.block_attachments_from_strangers)}
        title={t("app.block_stranger_attachments")}
        description={t("app.block_stranger_attachments_description")}
        onchange={onblockattachmentschange}
    />
    <SettingToggleRow
        id="block-all-from-strangers"
        checked={Boolean(config.block_all_from_strangers)}
        title={t("app.block_all_from_strangers")}
        description={t("app.block_all_from_strangers_description")}
        onchange={onblockallchange}
    />
    <SettingToggleRow
        id="show-unknown-contact-banner"
        checked={Boolean(config.show_unknown_contact_banner)}
        title={t("app.show_unknown_contact_banner")}
        description={t("app.show_unknown_contact_banner_description")}
        onchange={onunknownbannerchange}
    />
    <SettingToggleRow
        id="warn-on-stranger-links"
        checked={Boolean(config.warn_on_stranger_links)}
        title={t("app.warn_on_stranger_links")}
        description={t("app.warn_on_stranger_links_description")}
        onchange={onwarnlinkschange}
    />
</SettingsSectionBlock>
