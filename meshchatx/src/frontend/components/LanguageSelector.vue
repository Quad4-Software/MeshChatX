<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="relative">
        <button
            type="button"
            class="relative rounded-full p-1.5 sm:p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-zinc-800 transition-colors"
            :title="$t('app.language')"
            @click.stop="toggleDropdown"
        >
            <MaterialDesignIcon icon-name="translate" class="w-5 h-5 sm:w-6 sm:h-6" />
        </button>

        <Teleport to="body">
            <div
                v-if="isDropdownOpen"
                v-click-outside="closeDropdown"
                class="fixed w-48 bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 rounded-2xl shadow-xl z-[9999] overflow-hidden"
                :style="dropdownStyle"
            >
                <div class="p-2">
                    <button
                        v-for="lang in languages"
                        :key="lang.code"
                        type="button"
                        class="w-full px-4 py-2 text-left rounded-lg hover:bg-gray-100 dark:hover:bg-zinc-800 transition-colors flex items-center justify-between"
                        :class="{
                            'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400':
                                currentLanguage === lang.code,
                            'text-gray-900 dark:text-zinc-100': currentLanguage !== lang.code,
                        }"
                        @click="selectLanguage(lang.code)"
                    >
                        <span class="font-medium">{{ lang.name }}</span>
                        <MaterialDesignIcon v-if="currentLanguage === lang.code" icon-name="check" class="w-5 h-5" />
                    </button>
                </div>
            </div>
        </Teleport>
    </div>
</template>

<script>
import MaterialDesignIcon from "./MaterialDesignIcon.vue";

const localeModules = import.meta.glob("../locales/*.json", { eager: true });
const discoveredLanguages = Object.entries(localeModules)
    .map(([filePath, mod]) => ({
        code: filePath.match(/\/([^/]+)\.json$/)[1],
        name: mod.default?._languageName || filePath.match(/\/([^/]+)\.json$/)[1],
    }))
    .sort((a, b) => {
        if (a.code === "en") return -1;
        if (b.code === "en") return 1;
        return a.name.localeCompare(b.name);
    });

export default {
    name: "LanguageSelector",
    components: {
        MaterialDesignIcon,
    },
    directives: {
        "click-outside": {
            mounted(el, binding) {
                el.clickOutsideEvent = function (event) {
                    if (!(el === event.target || el.contains(event.target))) {
                        binding.value();
                    }
                };
                document.addEventListener("click", el.clickOutsideEvent);
            },
            unmounted(el) {
                document.removeEventListener("click", el.clickOutsideEvent);
            },
        },
    },
    emits: ["language-change"],
    data() {
        return {
            isDropdownOpen: false,
            dropdownPosition: { top: 0, left: 0 },
        };
    },
    computed: {
        currentLanguage() {
            return this.$i18n.locale;
        },
        languages() {
            return discoveredLanguages;
        },
        dropdownStyle() {
            return {
                top: `${this.dropdownPosition.top}px`,
                left: `${this.dropdownPosition.left}px`,
            };
        },
    },
    methods: {
        toggleDropdown(event) {
            this.isDropdownOpen = !this.isDropdownOpen;
            if (this.isDropdownOpen) {
                this.updateDropdownPosition(event);
            }
        },
        updateDropdownPosition(event) {
            const button = event.currentTarget;
            const rect = button.getBoundingClientRect();
            this.dropdownPosition = {
                top: rect.bottom + 8,
                left: Math.max(8, rect.right - 192), // 192px is w-48
            };
        },
        closeDropdown() {
            this.isDropdownOpen = false;
        },
        async selectLanguage(langCode) {
            if (this.currentLanguage === langCode) {
                this.closeDropdown();
                return;
            }

            this.$emit("language-change", langCode);
            this.closeDropdown();
        },
    },
};
</script>
