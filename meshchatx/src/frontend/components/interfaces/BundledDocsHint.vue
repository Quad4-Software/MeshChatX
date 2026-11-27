<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <p :class="paragraphClass">
        <span>{{ $t(hintI18nKey) }}</span>
        {{ " " }}
        <button
            type="button"
            class="text-sem-accent hover:underline font-medium cursor-pointer inline p-0 border-0 bg-transparent text-left align-baseline text-[inherit]"
            @click="openDocs"
        >
            {{ $t(linkI18nKey) }}
        </button>
    </p>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import { RETICULUM_MANUAL_INTERFACES_COMMON_OPTIONS_REL } from "../../js/reticulumDocsEntryUrl.js";
import { openBundledReticulumManualPath } from "../../js/reticulumDocsNavigation.js";

const props = withDefaults(
    defineProps<{
        paragraphClass?: string;
        hintI18nKey?: string;
        linkI18nKey?: string;
        docsRelPath?: string;
    }>(),
    {
        paragraphClass: "text-xs text-sem-fg-muted mt-0.5",
        hintI18nKey: "interfaces.discovery_default_bootstrap_only_hint",
        linkI18nKey: "interfaces.discovery_default_bootstrap_docs_link",
        docsRelPath: RETICULUM_MANUAL_INTERFACES_COMMON_OPTIONS_REL,
    }
);

const router = useRouter();

function openDocs() {
    openBundledReticulumManualPath(router, props.docsRelPath);
}
</script>
