<template>
    <v-dialog
        v-if="!isPage"
        v-model="visible"
        :fullscreen="isMobile"
        max-width="800"
        transition="dialog-bottom-transition"
        class="changelog-dialog"
        @update:model-value="onVisibleUpdate"
    >
        <v-card class="flex flex-col h-full bg-white dark:bg-zinc-900 border-0 overflow-hidden">
            <!-- Header -->
            <v-toolbar flat color="transparent" class="px-4 border-b dark:border-zinc-800">
                <div class="flex items-center">
                    <div class="p-1 mr-3">
                        <img src="../public/favicons/favicon-512x512.png" class="w-8 h-8 object-contain" alt="Logo" />
                    </div>
                    <v-toolbar-title class="text-xl font-bold tracking-tight text-gray-900 dark:text-white">
                        {{ $t("app.changelog_title", "What's New") }}
                    </v-toolbar-title>
                    <v-chip
                        v-if="version"
                        size="x-small"
                        color="blue"
                        variant="flat"
                        class="ml-3 font-black text-[10px] px-2 h-5 tracking-tighter uppercase rounded-sm"
                    >
                        v{{ version }}
                    </v-chip>
                </div>
                <v-spacer></v-spacer>
                <v-btn
                    icon
                    size="small"
                    variant="text"
                    class="text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/10"
                    @click="close"
                >
                    <v-icon>mdi-close</v-icon>
                </v-btn>
            </v-toolbar>

            <!-- Content -->
            <v-card-text class="flex-1 overflow-y-auto px-6 py-8">
                <div v-if="loading" class="flex flex-col items-center justify-center h-full space-y-4">
                    <v-progress-circular indeterminate color="blue" size="64"></v-progress-circular>
                    <div class="text-gray-500 dark:text-zinc-400 font-medium">Loading changelog...</div>
                </div>

                <div v-else-if="error" class="flex flex-col items-center justify-center h-full text-center space-y-4">
                    <v-icon icon="mdi-alert-circle-outline" size="64" color="red"></v-icon>
                    <div class="text-red-500 font-bold text-lg">{{ error }}</div>
                    <v-btn
                        color="blue"
                        variant="flat"
                        class="font-bold uppercase px-6"
                        rounded="lg"
                        @click="fetchChangelog"
                    >
                        Retry
                    </v-btn>
                </div>

                <div
                    v-else
                    class="changelog-content max-w-none prose dark:prose-invert text-gray-900 dark:text-zinc-100"
                >
                    <!-- eslint-disable-next-line vue/no-v-html -->
                    <div v-html="changelogHtml"></div>
                </div>
            </v-card-text>

            <!-- Footer -->
            <v-divider class="dark:border-zinc-800"></v-divider>
            <v-card-actions class="px-6 py-4 bg-gray-50 dark:bg-zinc-950/50 flex-wrap gap-y-2">
                <div class="flex flex-col">
                    <v-checkbox
                        v-model="dontShowAgain"
                        :label="$t('app.do_not_show_again', 'Do not show again for this version')"
                        density="compact"
                        hide-details
                        color="blue"
                        class="my-0 text-gray-700 dark:text-zinc-300 font-medium"
                    ></v-checkbox>
                    <v-checkbox
                        v-model="dontShowEver"
                        :label="$t('app.do_not_show_ever', 'Do not show ever again')"
                        density="compact"
                        hide-details
                        color="red"
                        class="my-0 text-gray-700 dark:text-zinc-300 font-medium"
                    ></v-checkbox>
                </div>
                <v-spacer></v-spacer>
                <v-btn
                    variant="flat"
                    color="blue"
                    class="px-8 font-black tracking-tighter uppercase text-white dark:text-zinc-900"
                    rounded="xl"
                    @click="close"
                >
                    {{ $t("common.close", "Close") }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>

    <div v-else class="flex flex-col h-full bg-white dark:bg-zinc-950 overflow-hidden">
        <div class="flex-1 overflow-y-auto px-6 md:px-12 py-10">
            <div class="max-w-4xl mx-auto">
                <div class="flex items-center gap-4 mb-8">
                    <div class="p-2">
                        <img src="../public/favicons/favicon-512x512.png" class="w-16 h-16 object-contain" alt="Logo" />
                    </div>
                    <div>
                        <h1 class="text-4xl font-black text-gray-900 dark:text-white tracking-tighter uppercase mb-1">
                            {{ $t("app.changelog_title", "What's New") }}
                        </h1>
                        <div class="flex items-center gap-2">
                            <v-chip
                                color="blue"
                                variant="flat"
                                size="x-small"
                                class="font-black text-[10px] px-2 h-5 rounded-sm"
                            >
                                v{{ version }}
                            </v-chip>
                            <span class="text-sm text-gray-500 font-medium">Full release history</span>
                        </div>
                    </div>
                </div>

                <div v-if="loading" class="flex flex-col items-center justify-center py-20 space-y-4">
                    <v-progress-circular indeterminate color="blue" size="64"></v-progress-circular>
                </div>

                <div v-else-if="error" class="flex flex-col items-center justify-center py-20 text-center space-y-4">
                    <v-icon icon="mdi-alert-circle-outline" size="64" color="red"></v-icon>
                    <div class="text-red-500 font-bold text-lg">{{ error }}</div>
                    <v-btn
                        color="blue"
                        variant="flat"
                        class="font-bold uppercase px-6"
                        rounded="lg"
                        @click="fetchChangelog"
                    >
                        Retry
                    </v-btn>
                </div>

                <div v-else class="changelog-content max-w-none prose dark:prose-invert pb-20">
                    <!-- eslint-disable-next-line vue/no-v-html -->
                    <div v-html="changelogHtml"></div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    name: "ChangelogModal",
    props: {
        appVersion: {
            type: String,
            default: "",
        },
    },
    data() {
        return {
            visible: false,
            loading: true,
            error: null,
            changelogHtml: "",
            version: "",
            dontShowAgain: false,
            dontShowEver: false,
        };
    },
    computed: {
        currentVersion() {
            return this.version || this.appVersion;
        },
        isPage() {
            return this.$route?.meta?.isPage === true;
        },
        isMobile() {
            return window.innerWidth < 640;
        },
    },
    mounted() {
        if (this.isPage) {
            this.fetchChangelog();
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
                const response = await window.axios.get("/api/v1/app/changelog");
                this.version = response.data.version;

                // Process HTML to make version headers look better
                // Find [x.x.x] and wrap in a styled span
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
            // mark as seen for current version automatically on close if not already marked
            if (!this.dontShowEver && !this.dontShowAgain) {
                try {
                    await window.axios.post("/api/v1/app/changelog/seen", {
                        version: this.currentVersion || "0.0.0",
                    });
                } catch (e) {
                    console.error("Failed to auto-mark changelog as seen:", e);
                }
            } else {
                await this.markAsSeen();
            }
            this.visible = false;
        },
        async markAsSeen() {
            if (this.dontShowEver) {
                try {
                    await window.axios.post("/api/v1/app/changelog/seen", {
                        version: "999.999.999",
                    });
                } catch (e) {
                    console.error("Failed to mark changelog as seen forever:", e);
                }
            } else if (this.dontShowAgain) {
                try {
                    await window.axios.post("/api/v1/app/changelog/seen", {
                        version: this.currentVersion,
                    });
                } catch (e) {
                    console.error("Failed to mark changelog as seen for this version:", e);
                }
            }
        },
        async onVisibleUpdate(val) {
            if (!val) {
                // handle case where dialog is closed by clicking outside or ESC
                await this.markAsSeen();
            }
        },
    },
};
</script>

<style>
.changelog-dialog .v-overlay__content {
    border-radius: 0.5rem !important;
    overflow: hidden;
}

.changelog-content {
    @apply leading-relaxed !important;
}

.changelog-content h1 {
    @apply text-3xl font-black mt-2 mb-6 text-gray-900 dark:text-white tracking-tight uppercase border-b-2 border-gray-100 dark:border-zinc-800 pb-2 !important;
}

.changelog-content h2 {
    @apply flex items-center gap-3 text-xl font-bold mt-8 mb-4 text-gray-900 dark:text-white !important;
}

/* Style for [v4.0.0] style headers in markdown */
.changelog-content h2::before {
    content: "VERSION";
    @apply text-[10px] font-black bg-blue-500 text-white px-1.5 py-0.5 rounded-sm tracking-tighter !important;
}

.changelog-content h3 {
    @apply text-lg font-bold mt-6 mb-3 text-blue-600 dark:text-blue-400 flex items-center gap-2 !important;
}

.changelog-content h3::before {
    content: "•";
    @apply text-blue-500 font-black !important;
}

.changelog-content p {
    @apply my-4 text-gray-700 dark:text-zinc-300 leading-relaxed !important;
}

.changelog-content ul {
    @apply my-6 space-y-3 list-disc pl-6 !important;
}

.changelog-content li {
    @apply text-gray-600 dark:text-zinc-400 transition-colors hover:text-gray-900 dark:hover:text-white !important;
}

.changelog-content strong {
    @apply font-bold text-gray-900 dark:text-zinc-100 !important;
}

.changelog-content code {
    @apply bg-blue-50 dark:bg-blue-900/20 px-1.5 py-0.5 rounded-sm text-blue-700 dark:text-blue-300 font-mono text-[0.85em] border border-blue-100 dark:border-blue-800/30 !important;
}

.changelog-content hr {
    @apply my-10 border-gray-100 dark:border-zinc-800 !important;
}

/* Highlight tags like [4.0.0] if they are inside the text */
.changelog-content h2 {
    counter-increment: version-counter;
}

.changelog-content h2 {
    @apply py-2 px-4 bg-gray-50 dark:bg-zinc-800/50 rounded-md border border-gray-100 dark:border-zinc-800 !important;
}

.changelog-content .version-tag {
    @apply bg-blue-600 text-white px-2 py-0.5 rounded-sm font-black text-sm tracking-tighter !important;
}
</style>
