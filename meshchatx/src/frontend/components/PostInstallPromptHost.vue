<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <AppUpdatePrompt
        :model-value="visible"
        :title="resolvedTitle"
        :description="resolvedDescription"
        :primary-label="resolvedPrimaryLabel"
        :secondary-label="resolvedSecondaryLabel"
        :busy="busy"
        @update:model-value="onVisibleUpdate"
        @primary="onPrimary"
        @secondary="onSecondary"
    />
</template>

<script>
import AppUpdatePrompt from "./AppUpdatePrompt.vue";
import { listPostInstallPromptsByPriority } from "../js/registries/postInstallPromptRegistry.js";
import { markPromptSeen, shouldShowPrompt } from "../js/postInstallPromptState.js";

export default {
    name: "PostInstallPromptHost",
    components: { AppUpdatePrompt },
    emits: ["completed", "dismissed"],
    data() {
        return {
            visible: false,
            busy: false,
            activeEntry: null,
        };
    },
    computed: {
        resolvedTitle() {
            if (!this.activeEntry?.titleKey) {
                return "";
            }
            return this.$t(this.activeEntry.titleKey);
        },
        resolvedDescription() {
            if (!this.activeEntry?.descriptionKey) {
                return "";
            }
            return this.$t(this.activeEntry.descriptionKey);
        },
        resolvedPrimaryLabel() {
            const key = this.activeEntry?.primaryLabelKey || "common.continue";
            return this.$t(key);
        },
        resolvedSecondaryLabel() {
            if (!this.activeEntry?.secondaryLabelKey) {
                return "";
            }
            return this.$t(this.activeEntry.secondaryLabelKey);
        },
    },
    methods: {
        /**
         * Find and show the next pending registry prompt.
         * @returns {Promise<boolean>} true if a prompt was opened
         */
        async showNext() {
            if (this.visible) {
                return true;
            }
            const pending = await this.findNextPending();
            if (!pending) {
                return false;
            }
            this.activeEntry = pending;
            this.visible = true;
            return true;
        },
        /**
         * @returns {Promise<import('../js/registries/postInstallPromptRegistry.js').PostInstallPromptEntry | null>}
         */
        async findNextPending() {
            for (const entry of listPostInstallPromptsByPriority()) {
                if (!shouldShowPrompt(entry.id, entry.revision)) {
                    continue;
                }
                if (typeof entry.shouldShow === "function") {
                    try {
                        const ok = await entry.shouldShow();
                        if (!ok) {
                            continue;
                        }
                    } catch (e) {
                        console.error(`post-install prompt ${entry.id} shouldShow failed`, e);
                        continue;
                    }
                }
                return entry;
            }
            return null;
        },
        hide() {
            this.visible = false;
            this.activeEntry = null;
            this.busy = false;
        },
        onVisibleUpdate(val) {
            this.visible = val;
            if (!val) {
                this.$emit("dismissed");
                this.activeEntry = null;
                this.busy = false;
            }
        },
        dismissActive() {
            const entry = this.activeEntry;
            if (entry) {
                markPromptSeen(entry.id, entry.revision);
            }
            this.hide();
            this.$emit("completed", { id: entry?.id, revision: entry?.revision });
        },
        async onPrimary() {
            if (this.busy || !this.activeEntry) {
                return;
            }
            this.busy = true;
            try {
                const entry = this.activeEntry;
                let keepOpen = false;
                if (typeof entry.onPrimary === "function") {
                    const result = await entry.onPrimary({ entry });
                    keepOpen = result === false;
                }
                if (keepOpen) {
                    return;
                }
                if (entry.dismissOnPrimary !== false) {
                    this.dismissActive();
                } else {
                    this.hide();
                    this.$emit("completed", { id: entry.id, revision: entry.revision });
                }
            } catch (e) {
                console.error("post-install prompt primary action failed", e);
            } finally {
                this.busy = false;
            }
        },
        async onSecondary() {
            if (this.busy || !this.activeEntry?.secondaryLabelKey) {
                return;
            }
            this.busy = true;
            try {
                const entry = this.activeEntry;
                let keepOpen = false;
                if (typeof entry.onSecondary === "function") {
                    const result = await entry.onSecondary({ entry });
                    keepOpen = result === false;
                }
                if (keepOpen) {
                    return;
                }
                if (entry.dismissOnSecondary !== false) {
                    this.dismissActive();
                } else {
                    this.hide();
                    this.$emit("completed", { id: entry.id, revision: entry.revision });
                }
            } catch (e) {
                console.error("post-install prompt secondary action failed", e);
            } finally {
                this.busy = false;
            }
        },
    },
};
</script>
