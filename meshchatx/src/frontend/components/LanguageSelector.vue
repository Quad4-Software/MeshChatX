<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="relative">
        <button
            type="button"
            class="relative rounded-full p-1.5 text-sem-fg-muted hover:bg-sem-surface-muted transition-colors"
            :title="$t('app.language')"
            @click.stop="toggleDropdown"
        >
            <MaterialDesignIcon icon-name="translate" class="size-5" />
        </button>

        <Teleport to="body">
            <div
                v-if="isDropdownOpen"
                ref="languageDropdown"
                v-click-outside="closeDropdown"
                class="fixed w-48 bg-sem-surface border border-sem-border rounded-2xl shadow-xl z-9999 overflow-x-hidden"
                :style="dropdownStyle"
            >
                <div class="p-2">
                    <button
                        v-for="lang in languages"
                        :key="lang.code"
                        type="button"
                        class="w-full px-4 py-2 text-left rounded-lg hover:bg-sem-surface-muted transition-colors flex items-center justify-between"
                        :class="{
                            'bg-sem-surface-muted text-sem-accent': currentLanguage === lang.code,
                            'text-sem-fg': currentLanguage !== lang.code,
                        }"
                        @click.stop="selectLanguage(lang.code)"
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
import { clampFloatingToViewport } from "../js/clampFloatingToViewport.js";
import { ensureLocaleMessages, listLocaleCodes, setLocale } from "../js/localeLoader.js";

const LANGUAGE_NAMES = {
    de: "Deutsch",
    en: "English",
    es: "Español",
    fi: "Suomi",
    fr: "Français",
    it: "Italiano",
    nl: "Nederlands",
    ru: "Русский",
    zh: "中文",
};

const discoveredLanguages = listLocaleCodes().map((code) => ({
    code,
    name: LANGUAGE_NAMES[code] || code,
}));

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
            dropdownMaxHeight: null,
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
            const style = {
                top: `${this.dropdownPosition.top}px`,
                left: `${this.dropdownPosition.left}px`,
            };
            if (this.dropdownMaxHeight != null) {
                style.maxHeight = `${this.dropdownMaxHeight}px`;
                style.overflowY = "auto";
            } else {
                style.overflow = "hidden";
            }
            return style;
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
            this.dropdownMaxHeight = null;
            this.dropdownPosition = {
                top: rect.bottom + 8,
                left: Math.max(8, rect.right - 192),
            };
            this.$nextTick(() => {
                const panel = this.$refs.languageDropdown;
                if (!panel) return;
                const pr = panel.getBoundingClientRect();
                const { left, top, maxHeight } = clampFloatingToViewport(pr.left, pr.top, pr.width, pr.height);
                this.dropdownPosition = { left, top };
                this.dropdownMaxHeight = maxHeight;
            });
        },
        closeDropdown() {
            this.isDropdownOpen = false;
        },
        async selectLanguage(langCode) {
            if (this.currentLanguage === langCode) {
                this.closeDropdown();
                return;
            }

            // Apply immediately. Parent persists config. Options API this.$i18n is a
            // locale-only proxy under legacy:false so setLocale uses registerUiI18n.
            try {
                const ok = await setLocale(this.$i18n, langCode);
                if (!ok) {
                    await ensureLocaleMessages(this.$i18n, langCode);
                }
            } catch {
                // Locale pack may be unavailable in tests or offline shells.
            }
            this.$emit("language-change", langCode);
            this.closeDropdown();
        },
    },
};
</script>
