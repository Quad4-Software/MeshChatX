<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-slate-50 dark:bg-zinc-950">
        <div
            class="flex-1 overflow-y-auto w-full px-4 md:px-5 lg:px-8 py-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]"
        >
            <div class="space-y-4 w-full max-w-4xl mx-auto">
                <div class="glass-card space-y-5">
                    <div class="space-y-2">
                        <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                            Text Translation
                        </div>
                        <div class="text-2xl font-semibold text-gray-900 dark:text-white">Translator</div>
                        <div class="text-sm text-gray-600 dark:text-gray-300">
                            Translate text using LibreTranslate API or local Argos Translate.
                        </div>
                    </div>

                    <div
                        v-if="config && !config.translator_enabled"
                        class="p-4 rounded-xl bg-amber-50 dark:bg-amber-900/10 border border-amber-200/50 dark:border-amber-800/30"
                    >
                        <div class="flex items-start gap-3">
                            <div class="p-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
                                <MaterialDesignIcon
                                    icon-name="alert-outline"
                                    class="size-5 text-amber-600 dark:text-amber-400"
                                />
                            </div>
                            <div class="flex-1 text-sm text-amber-800 dark:text-amber-200">
                                <p class="font-bold mb-1">Translator is Disabled</p>
                                <p class="opacity-90">
                                    The translation service is currently disabled in your settings. You can enable it
                                    under
                                    <RouterLink :to="{ name: 'settings' }" class="font-bold underline"
                                        >Settings</RouterLink
                                    >.
                                </p>
                            </div>
                        </div>
                    </div>

                    <div class="border-b border-gray-200 dark:border-zinc-700">
                        <div class="flex -mb-px">
                            <button
                                type="button"
                                class="px-4 py-2 text-sm font-semibold border-b-2 transition-colors"
                                :class="
                                    translationMode === 'argos'
                                        ? 'border-blue-500 text-blue-600 dark:border-blue-400 dark:text-blue-300'
                                        : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                                "
                                @click="translationMode = 'argos'"
                            >
                                Argos Translate
                            </button>
                            <button
                                type="button"
                                class="px-4 py-2 text-sm font-semibold border-b-2 transition-colors"
                                :class="
                                    translationMode === 'libretranslate'
                                        ? 'border-blue-500 text-blue-600 dark:border-blue-400 dark:text-blue-300'
                                        : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                                "
                                @click="translationMode = 'libretranslate'"
                            >
                                LibreTranslate
                            </button>
                        </div>
                    </div>

                    <div
                        v-if="translationMode === 'libretranslate'"
                        class="p-3 rounded-lg bg-gray-50 dark:bg-zinc-800/50 border border-gray-100 dark:border-zinc-700/50"
                    >
                        <label class="glass-label mb-2">LibreTranslate API Server</label>
                        <input
                            v-model="libretranslateUrl"
                            type="text"
                            placeholder="http://localhost:5000"
                            class="input-field"
                        />
                        <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            Enter the base URL of your LibreTranslate server (e.g., http://localhost:5000)
                        </div>
                    </div>

                    <div class="grid lg:grid-cols-2 gap-4">
                        <div>
                            <label class="glass-label">Source Language</label>
                            <select v-model="sourceLang" class="input-field">
                                <option v-if="translationMode === 'libretranslate'" value="auto">Auto-detect</option>
                                <option v-for="lang in filteredLanguages" :key="`src-${lang.code}`" :value="lang.code">
                                    {{ lang.name }} ({{ lang.code }})
                                </option>
                            </select>
                        </div>
                        <div>
                            <label class="glass-label">Target Language</label>
                            <select v-model="targetLang" class="input-field">
                                <option value="">Select target language</option>
                                <option v-for="lang in filteredLanguages" :key="`tgt-${lang.code}`" :value="lang.code">
                                    {{ lang.name }} ({{ lang.code }})
                                </option>
                            </select>
                        </div>
                    </div>

                    <div
                        v-if="translationMode === 'argos' && !hasArgos"
                        class="p-4 rounded-xl bg-amber-50 dark:bg-amber-900/10 border border-amber-200/50 dark:border-amber-800/30"
                    >
                        <div class="flex items-start gap-3">
                            <div class="p-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
                                <MaterialDesignIcon
                                    icon-name="information-outline"
                                    class="size-5 text-amber-600 dark:text-amber-400"
                                />
                            </div>
                            <div class="flex-1 text-sm text-amber-800 dark:text-amber-200">
                                <p class="font-bold mb-1">Argos Translate not detected</p>
                                <p class="mb-4 opacity-90">
                                    To use local translation, you must install the Argos Translate package using one of
                                    the following methods:
                                </p>

                                <div class="grid sm:grid-cols-2 gap-4">
                                    <div class="space-y-2">
                                        <div class="flex items-center justify-between">
                                            <span class="text-xs font-semibold uppercase tracking-wider opacity-70"
                                                >Method 1: pip (venv)</span
                                            >
                                            <button
                                                class="text-amber-600 dark:text-amber-400 hover:scale-110 transition-transform"
                                                @click="copyToClipboard('pip install argostranslate')"
                                            >
                                                <MaterialDesignIcon icon-name="content-copy" class="size-4" />
                                            </button>
                                        </div>
                                        <div
                                            class="bg-amber-100/50 dark:bg-black/30 p-2 rounded font-mono text-xs break-all"
                                        >
                                            pip install argostranslate
                                        </div>
                                    </div>

                                    <div class="space-y-2">
                                        <div class="flex items-center justify-between">
                                            <span class="text-xs font-semibold uppercase tracking-wider opacity-70"
                                                >Method 2: pipx</span
                                            >
                                            <button
                                                class="text-amber-600 dark:text-amber-400 hover:scale-110 transition-transform"
                                                @click="copyToClipboard('pipx install argostranslate')"
                                            >
                                                <MaterialDesignIcon icon-name="content-copy" class="size-4" />
                                            </button>
                                        </div>
                                        <div
                                            class="bg-amber-100/50 dark:bg-black/30 p-2 rounded font-mono text-xs break-all"
                                        >
                                            pipx install argostranslate
                                        </div>
                                    </div>
                                </div>
                                <p class="mt-4 text-xs opacity-70 italic">
                                    Note: After installation, you may need to restart the application and install
                                    language packages via the Argos Translate CLI.
                                </p>
                            </div>
                        </div>
                    </div>

                    <div
                        v-if="translationMode === 'argos' && hasArgos && !hasArgosLanguages"
                        class="p-4 rounded-xl bg-blue-50 dark:bg-blue-900/10 border border-blue-200/50 dark:border-blue-800/30"
                    >
                        <div class="flex items-start gap-3">
                            <div class="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                                <MaterialDesignIcon
                                    icon-name="information-outline"
                                    class="size-5 text-blue-600 dark:text-blue-400"
                                />
                            </div>
                            <div class="flex-1 text-sm text-blue-800 dark:text-blue-200">
                                <p class="font-bold mb-1">No language packages detected</p>
                                <p class="mb-4 opacity-90">
                                    Argos Translate is installed but no language packages are available. Install
                                    language packages using the buttons below or the CLI commands:
                                </p>

                                <div class="space-y-3">
                                    <div class="space-y-2">
                                        <div class="flex items-center justify-between">
                                            <span class="text-xs font-semibold uppercase tracking-wider opacity-70"
                                                >Install all languages</span
                                            >
                                            <div class="flex gap-2">
                                                <button
                                                    class="text-blue-600 dark:text-blue-400 hover:scale-110 transition-transform"
                                                    @click="copyToClipboard('argospm install translate')"
                                                >
                                                    <MaterialDesignIcon icon-name="content-copy" class="size-4" />
                                                </button>
                                            </div>
                                        </div>
                                        <div class="flex gap-2">
                                            <button
                                                type="button"
                                                class="primary-chip px-3 py-1.5 text-xs"
                                                :disabled="isInstallingLanguages"
                                                @click="installLanguages('translate')"
                                            >
                                                <span
                                                    v-if="isInstallingLanguages"
                                                    class="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin mr-1"
                                                ></span>
                                                <MaterialDesignIcon v-else icon-name="download" class="w-3 h-3" />
                                                Install All
                                            </button>
                                            <div
                                                class="bg-blue-100/50 dark:bg-black/30 p-2 rounded font-mono text-xs break-all flex-1"
                                            >
                                                argospm install translate
                                            </div>
                                        </div>
                                    </div>

                                    <div class="space-y-2">
                                        <div class="flex items-center justify-between">
                                            <span class="text-xs font-semibold uppercase tracking-wider opacity-70"
                                                >Install specific language pair (example: English to German)</span
                                            >
                                            <button
                                                class="text-blue-600 dark:text-blue-400 hover:scale-110 transition-transform"
                                                @click="copyToClipboard('argospm install translate-en_de')"
                                            >
                                                <MaterialDesignIcon icon-name="content-copy" class="size-4" />
                                            </button>
                                        </div>
                                        <div
                                            class="bg-blue-100/50 dark:bg-black/30 p-2 rounded font-mono text-xs break-all"
                                        >
                                            argospm install translate-en_de
                                        </div>
                                    </div>
                                </div>
                                <p class="mt-4 text-xs opacity-70 italic">
                                    After installing language packages, click "Refresh Languages" to reload available
                                    languages.
                                </p>
                            </div>
                        </div>
                    </div>

                    <div>
                        <label class="glass-label">Text to Translate</label>
                        <textarea
                            v-model="inputText"
                            rows="6"
                            placeholder="Enter text to translate..."
                            class="input-field"
                            :disabled="isTranslating"
                        ></textarea>
                    </div>

                    <div class="flex gap-2">
                        <button
                            type="button"
                            class="primary-chip px-4 py-2 text-sm"
                            :disabled="!canTranslate || isTranslating"
                            @click="translateText"
                        >
                            <span
                                v-if="isTranslating"
                                class="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"
                            ></span>
                            <MaterialDesignIcon v-else icon-name="translate" class="w-4 h-4" />
                            {{ isTranslating ? "Translating..." : "Translate" }}
                        </button>
                        <button
                            type="button"
                            class="secondary-chip px-4 py-2 text-sm"
                            :disabled="!targetLang || isTranslating"
                            @click="swapLanguages"
                        >
                            <MaterialDesignIcon icon-name="swap-horizontal" class="w-4 h-4" />
                            Swap
                        </button>
                        <button type="button" class="secondary-chip px-4 py-2 text-sm" @click="clearText">
                            <MaterialDesignIcon icon-name="broom" class="w-4 h-4" />
                            Clear
                        </button>
                    </div>

                    <div v-if="translationResult" class="space-y-2">
                        <div class="flex items-center justify-between">
                            <div class="text-sm font-semibold text-gray-900 dark:text-white">Translation</div>
                            <div class="text-xs text-gray-500 dark:text-gray-400">
                                Source: {{ translationResult.source }}
                            </div>
                        </div>
                        <div
                            class="p-4 rounded-lg bg-gray-50 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700"
                        >
                            <div class="text-gray-900 dark:text-white whitespace-pre-wrap">
                                {{ translationResult.translated_text }}
                            </div>
                        </div>
                        <div class="text-xs text-gray-500 dark:text-gray-400">
                            Detected: {{ translationResult.source_lang }} → {{ translationResult.target_lang }}
                        </div>
                    </div>

                    <div
                        v-if="error"
                        class="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300"
                    >
                        {{ error }}
                    </div>
                </div>

                <div class="glass-card space-y-3">
                    <div class="text-sm font-semibold text-gray-900 dark:text-white">Available Languages</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400 mb-2">
                        Languages are loaded from LibreTranslate API or Argos Translate packages.
                    </div>
                    <div class="flex flex-wrap gap-2">
                        <span
                            v-for="lang in filteredLanguages"
                            :key="lang.code"
                            class="px-2 py-1 rounded text-xs bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-gray-300"
                        >
                            {{ lang.name }} ({{ lang.code }})
                            <span class="text-gray-500 dark:text-gray-500">- {{ lang.source }}</span>
                        </span>
                    </div>
                    <div class="flex gap-2 mt-2">
                        <button type="button" class="secondary-chip px-4 py-2 text-sm" @click="loadLanguages">
                            <MaterialDesignIcon icon-name="refresh" class="w-4 h-4" />
                            Refresh Languages
                        </button>
                        <button
                            v-if="translationMode === 'argos' && hasArgos"
                            type="button"
                            class="primary-chip px-4 py-2 text-sm"
                            :disabled="isInstallingLanguages"
                            @click="installLanguages('translate')"
                        >
                            <span
                                v-if="isInstallingLanguages"
                                class="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"
                            ></span>
                            <MaterialDesignIcon v-else icon-name="download" class="w-4 h-4" />
                            Install All Languages
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import DialogUtils from "../../js/DialogUtils";
import ToastUtils from "../../js/ToastUtils";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

export default {
    name: "TranslatorPage",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            config: null,
            languages: [],
            sourceLang: "",
            targetLang: "",
            inputText: "",
            translationMode: "argos",
            libretranslateUrl: "http://localhost:5000",
            hasArgos: true,
            isTranslating: false,
            isInstallingLanguages: false,
            translationResult: null,
            error: null,
        };
    },
    computed: {
        canTranslate() {
            return (
                this.config?.translator_enabled &&
                this.inputText.trim().length > 0 &&
                this.targetLang &&
                this.targetLang !== this.sourceLang
            );
        },
        useArgos() {
            return this.translationMode === "argos";
        },
        hasArgosLanguages() {
            return this.languages.some((lang) => lang.source === "argos");
        },
        filteredLanguages() {
            if (this.translationMode === "argos") {
                return this.languages.filter((lang) => lang.source === "argos");
            } else {
                return this.languages.filter((lang) => lang.source === "libretranslate");
            }
        },
    },
    watch: {
        translationMode() {
            if (this.translationMode === "libretranslate" && !this.sourceLang) {
                this.sourceLang = "auto";
            } else if (this.translationMode === "argos" && this.sourceLang === "auto") {
                this.sourceLang = "";
            }
            this.loadLanguages();
        },
        libretranslateUrl() {
            if (this.translationMode === "libretranslate") {
                this.loadLanguages();
            }
        },
    },
    mounted() {
        this.getConfig();
    },
    methods: {
        async getConfig() {
            try {
                const response = await window.api.get("/api/v1/config");
                this.config = response.data.config;
                if (this.config.translator_enabled) {
                    this.loadLanguages();
                }
            } catch (e) {
                console.log(e);
            }
        },
        async loadLanguages() {
            if (this.config && !this.config.translator_enabled) {
                return;
            }
            try {
                const params = {};
                if (this.translationMode === "libretranslate" && this.libretranslateUrl) {
                    params.libretranslate_url = this.libretranslateUrl;
                }
                const response = await window.api.get("/api/v1/translator/languages", { params });
                this.languages = response.data.languages || [];
                this.hasArgos = response.data.has_argos;
            } catch (e) {
                console.error(e);
                DialogUtils.alert(this.$t("translator.failed_load_languages"));
            }
        },
        copyToClipboard(text) {
            navigator.clipboard.writeText(text);
            ToastUtils.success(this.$t("common.copied"));
        },
        async translateText() {
            if (!this.canTranslate || this.isTranslating) {
                return;
            }

            if (!this.sourceLang || !this.targetLang) {
                this.error = this.$t("translator.select_languages_warning");
                return;
            }

            if (this.translationMode === "argos" && this.sourceLang === "auto") {
                this.error = this.$t("translator.auto_detect_not_supported");
                return;
            }

            this.isTranslating = true;
            this.error = null;
            this.translationResult = null;

            try {
                const payload = {
                    text: this.inputText,
                    source_lang: this.sourceLang,
                    target_lang: this.targetLang,
                    use_argos: this.useArgos,
                };
                if (this.translationMode === "libretranslate" && this.libretranslateUrl) {
                    payload.libretranslate_url = this.libretranslateUrl;
                }
                const response = await window.api.post("/api/v1/translator/translate", payload);

                this.translationResult = response.data;
                if (this.translationResult.source_lang === "auto") {
                    this.sourceLang = this.translationResult.source_lang;
                }
            } catch (e) {
                console.error(e);
                this.error = e.response?.data?.message || this.$t("translator.failed_translate");
            } finally {
                this.isTranslating = false;
            }
        },
        swapLanguages() {
            if (!this.targetLang) {
                return;
            }

            if (
                this.translationResult &&
                this.translationResult.source_lang &&
                this.translationResult.source_lang !== "auto"
            ) {
                const temp = this.sourceLang;
                this.sourceLang = this.targetLang;
                this.targetLang = temp;

                if (this.translationResult.translated_text) {
                    this.inputText = this.translationResult.translated_text;
                    this.translationResult = null;
                }
            } else {
                const temp = this.sourceLang;
                if (this.translationMode === "argos") {
                    if (!this.targetLang) {
                        return;
                    }
                    this.sourceLang = this.targetLang;
                    this.targetLang = temp && temp !== "auto" ? temp : "";
                } else {
                    this.sourceLang = this.targetLang || "auto";
                    this.targetLang = temp && temp !== "auto" ? temp : "";
                }
            }
        },
        clearText() {
            this.inputText = "";
            this.translationResult = null;
            this.error = null;
        },
        async installLanguages(packageName) {
            if (this.isInstallingLanguages) {
                return;
            }

            this.isInstallingLanguages = true;
            this.error = null;

            try {
                const response = await window.api.post("/api/v1/translator/install-languages", {
                    package: packageName,
                });

                ToastUtils.success(response.data.message || "Languages installed successfully");
                await this.loadLanguages();
            } catch (e) {
                console.error(e);
                this.error =
                    e.response?.data?.message || "Failed to install languages. Make sure argospm is available in PATH.";
                ToastUtils.error(this.error);
            } finally {
                this.isInstallingLanguages = false;
            }
        },
    },
};
</script>
