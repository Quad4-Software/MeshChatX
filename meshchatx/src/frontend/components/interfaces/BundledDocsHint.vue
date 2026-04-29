<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <p :class="paragraphClass">
        <span>{{ $t(hintI18nKey) }}</span>
        {{ " " }}
        <button
            type="button"
            class="text-blue-600 dark:text-blue-400 hover:underline font-medium cursor-pointer inline p-0 border-0 bg-transparent text-left align-baseline text-[inherit]"
            @click="openDocs"
        >
            {{ $t(linkI18nKey) }}
        </button>
    </p>
</template>

<script>
import { RETICULUM_MANUAL_INTERFACES_COMMON_OPTIONS_REL } from "../../js/reticulumDocsEntryUrl.js";
import { openBundledReticulumManualPath } from "../../js/reticulumDocsNavigation.js";

export default {
    name: "BundledDocsHint",
    props: {
        paragraphClass: {
            type: String,
            default: "text-xs text-gray-500 dark:text-gray-400 mt-0.5",
        },
        hintI18nKey: {
            type: String,
            default: "interfaces.discovery_default_bootstrap_only_hint",
        },
        linkI18nKey: {
            type: String,
            default: "interfaces.discovery_default_bootstrap_docs_link",
        },
        docsRelPath: {
            type: String,
            default: RETICULUM_MANUAL_INTERFACES_COMMON_OPTIONS_REL,
        },
    },
    methods: {
        openDocs() {
            openBundledReticulumManualPath(this.$router, this.docsRelPath);
        },
    },
};
</script>
