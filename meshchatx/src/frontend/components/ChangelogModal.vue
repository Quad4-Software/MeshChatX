<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <AppModal
        v-if="!isPage"
        v-model="visible"
        :fullscreen="dialogFullscreen"
        :max-width="800"
        :show-close="true"
        panel-class="border-0"
        body-class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-6 sm:px-6 sm:py-8"
        @close="close"
    >
        <template #header>
            <div class="flex min-w-0 flex-1 items-center">
                <img :src="logoUrl" class="mr-3 size-8 object-contain" alt="Logo" />
                <h2 class="text-xl font-bold tracking-tight text-sem-fg">
                    {{ $t("app.changelog_title", "What's New") }}
                </h2>
                <span
                    v-if="version"
                    class="ml-3 inline-flex h-5 items-center rounded-xs bg-blue-600 px-2 text-[10px] font-black uppercase tracking-tighter text-white"
                >
                    v{{ version }}
                </span>
            </div>
        </template>

        <div v-if="loading">
            <LoadingState message="Loading changelog..." />
        </div>

        <div v-else-if="error" class="flex flex-col items-center justify-center space-y-4 py-10 text-center">
            <MaterialDesignIcon icon-name="alert-circle-outline" class="size-16 text-red-500" />
            <div class="text-lg font-bold text-red-500">{{ error }}</div>
            <button type="button" class="primary-chip px-6!" @click="fetchChangelog">Retry</button>
        </div>

        <div v-else class="changelog-content prose max-w-none dark:prose-invert text-sem-fg">
            <!-- eslint-disable-next-line vue/no-v-html -- sanitized via MarkdownRenderer -->
            <div v-html="changelogHtml"></div>
        </div>

        <template #actions>
            <div class="flex w-full flex-wrap items-center gap-y-2 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
                <div class="flex flex-col gap-1">
                    <label class="flex items-center gap-2 text-sm font-medium text-sem-fg-muted">
                        <input
                            v-model="dontShowAgain"
                            type="checkbox"
                            class="rounded-sm border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        {{ $t("app.do_not_show_again", "Do not show again for this version") }}
                    </label>
                    <label class="flex items-center gap-2 text-sm font-medium text-sem-fg-muted">
                        <input
                            v-model="dontShowEver"
                            type="checkbox"
                            class="rounded-sm border-gray-300 text-red-600 focus:ring-red-500"
                        />
                        {{ $t("app.do_not_show_ever", "Do not show ever again") }}
                    </label>
                </div>
                <div class="flex-1" />
                <button type="button" class="primary-chip h-10! rounded-xl! px-8!" @click="close">
                    {{ $t("common.close", "Close") }}
                </button>
            </div>
        </template>
    </AppModal>

    <div v-else class="flex h-full flex-col overflow-hidden bg-sem-surface">
        <div class="flex-1 overflow-y-auto px-6 py-10 md:px-12">
            <div class="mx-auto max-w-4xl">
                <div class="mb-8 flex items-center gap-4">
                    <img :src="logoUrl" class="size-16 object-contain" alt="Logo" />
                    <div>
                        <h1 class="mb-1 text-4xl font-black uppercase tracking-tighter text-sem-fg">
                            {{ $t("app.changelog_title", "What's New") }}
                        </h1>
                        <div class="flex items-center gap-2">
                            <span
                                class="inline-flex h-5 items-center rounded-xs bg-blue-600 px-2 text-[10px] font-black text-white"
                            >
                                v{{ version }}
                            </span>
                            <span class="text-sm font-medium text-gray-500">Full release history</span>
                        </div>
                    </div>
                </div>

                <div v-if="loading" class="py-20">
                    <LoadingState />
                </div>

                <div v-else-if="error" class="flex flex-col items-center justify-center space-y-4 py-20 text-center">
                    <MaterialDesignIcon icon-name="alert-circle-outline" class="size-16 text-red-500" />
                    <div class="text-lg font-bold text-red-500">{{ error }}</div>
                    <button type="button" class="primary-chip px-6!" @click="fetchChangelog">Retry</button>
                </div>

                <div v-else class="changelog-content prose max-w-none pb-20 dark:prose-invert">
                    <!-- eslint-disable-next-line vue/no-v-html -- sanitized via MarkdownRenderer -->
                    <div v-html="changelogHtml"></div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import AppModal from "./AppModal.vue";
import LoadingState from "./LoadingState.vue";
import MaterialDesignIcon from "./MaterialDesignIcon.vue";
import GlobalEmitter from "../js/GlobalEmitter";
import logoUrl from "../assets/images/logo.png";

export default {
    name: "ChangelogModal",
    components: {
        AppModal,
        LoadingState,
        MaterialDesignIcon,
    },
    props: {
        appVersion: {
            type: String,
            default: "",
        },
    },
    data() {
        return {
            logoUrl,
            visible: false,
            loading: true,
            error: null,
            changelogHtml: "",
            version: "",
            dontShowAgain: false,
            dontShowEver: false,
            windowWidth: typeof window !== "undefined" ? window.innerWidth : 1024,
        };
    },
    computed: {
        currentVersion() {
            return this.version || this.appVersion;
        },
        isPage() {
            return this.$route?.meta?.isPage === true;
        },
        dialogFullscreen() {
            return this.windowWidth < 768;
        },
    },
    watch: {
        visible(value) {
            if (!value) {
                this.onVisibleUpdate(false);
            }
        },
    },
    mounted() {
        this.onWindowResize = () => {
            this.windowWidth = window.innerWidth;
        };
        window.addEventListener("resize", this.onWindowResize, { passive: true });
        if (this.isPage) {
            this.fetchChangelog();
        }
    },
    beforeUnmount() {
        if (this.onWindowResize) {
            window.removeEventListener("resize", this.onWindowResize);
        }
    },
    methods: {
        async show() {
            this.visible = true;
            await this.fetchChangelog();
        },
        async fetchChangelog() {
            this.loading = true;
            this.error = null;
            try {
                const response = await window.api.get("/api/v1/app/changelog");
                this.version = response.data.version;

                let html = response.data.html;
                html = html.replace(/\[(\d+\.\d+\.\d+)\]/g, '<span class="version-tag">$1</span>');

                this.changelogHtml = html;
            } catch (e) {
                this.error = "Failed to load changelog.";
                console.error(e);
            } finally {
                this.loading = false;
            }
        },
        async close() {
            if (!this.dontShowEver && !this.dontShowAgain) {
                try {
                    await window.api.post("/api/v1/app/changelog/seen", {
                        version: this.currentVersion || "0.0.0",
                    });
                } catch (e) {
                    console.error("Failed to auto-mark changelog as seen:", e);
                }
            } else {
                await this.markAsSeen();
            }
            this.visible = false;
            GlobalEmitter.emit("changelog-closed");
        },
        async markAsSeen() {
            if (this.dontShowEver) {
                try {
                    await window.api.post("/api/v1/app/changelog/seen", {
                        version: "999.999.999",
                    });
                } catch (e) {
                    console.error("Failed to mark changelog as seen forever:", e);
                }
            } else if (this.dontShowAgain) {
                try {
                    await window.api.post("/api/v1/app/changelog/seen", {
                        version: this.currentVersion,
                    });
                } catch (e) {
                    console.error("Failed to mark changelog as seen for this version:", e);
                }
            }
        },
        async onVisibleUpdate(val) {
            if (!val) {
                await this.markAsSeen();
            }
        },
    },
};
</script>

<style>
@reference "../style.css";
.changelog-content {
    @apply leading-relaxed;
}

.changelog-content h1 {
    @apply text-3xl font-black mt-2 mb-6 text-sem-fg tracking-tight uppercase border-b-2 border-sem-border pb-2;
}

.changelog-content h2 {
    @apply flex items-center gap-3 text-xl font-bold mt-8 mb-4 text-sem-fg;
}

.changelog-content h2::before {
    content: "VERSION";
    @apply text-[10px] font-black bg-blue-500 text-white px-1.5 py-0.5 rounded-xs tracking-tighter;
}

.changelog-content h3 {
    @apply text-lg font-bold mt-6 mb-3 text-sem-accent flex items-center gap-2;
}

.changelog-content h3::before {
    content: "•";
    @apply text-blue-500 font-black;
}

.changelog-content p {
    @apply my-4 text-sem-fg-muted leading-relaxed;
}

.changelog-content ul {
    @apply my-6 space-y-3 list-disc pl-6;
}

.changelog-content li {
    @apply text-sem-fg-muted transition-colors hover:text-gray-900 dark:hover:text-white;
}

.changelog-content strong {
    @apply font-bold text-sem-fg;
}

.changelog-content code {
    @apply bg-sem-surface-muted px-1.5 py-0.5 rounded-xs text-blue-700 dark:text-blue-300 font-mono text-[0.85em] border border-blue-100 dark:border-blue-800/30;
}

.changelog-content hr {
    @apply my-10 border-sem-border;
}

.changelog-content h2 {
    counter-increment: version-counter;
}

.changelog-content h2 {
    @apply py-2 px-4 bg-gray-50 dark:bg-zinc-800/50 rounded-md border border-sem-border;
}

.changelog-content .version-tag {
    @apply bg-blue-600 text-white px-2 py-0.5 rounded-xs font-black text-sm tracking-tighter;
}
</style>
