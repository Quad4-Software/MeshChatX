<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { RETICULUM_MANUAL_INTERFACES_COMMON_OPTIONS_REL } from "../../../js/reticulumDocsEntryUrl.js";
    import { t } from "../../../js/i18n.js";

    interface Props {
        paragraphClass?: string;
        hintI18nKey?: string;
        linkI18nKey?: string;
        docsRelPath?: string;
    }

    let {
        paragraphClass = "text-xs text-sem-fg-muted mt-0.5",
        hintI18nKey = "interfaces.discovery_default_bootstrap_only_hint",
        linkI18nKey = "interfaces.discovery_default_bootstrap_docs_link",
        docsRelPath = RETICULUM_MANUAL_INTERFACES_COMMON_OPTIONS_REL,
    }: Props = $props();

    function openDocs() {
        window.location.hash = `#/docs?reticulum=${encodeURIComponent(docsRelPath)}`;
    }
</script>

<p class={paragraphClass}>
    <span>{t(hintI18nKey)}</span>
    <button
        type="button"
        class="text-sem-accent hover:underline font-medium cursor-pointer inline p-0 border-0 bg-transparent text-left align-baseline text-[inherit] ml-1"
        onclick={openDocs}
    >
        {t(linkI18nKey)}
    </button>
</p>
