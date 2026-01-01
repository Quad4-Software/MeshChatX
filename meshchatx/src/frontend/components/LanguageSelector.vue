<template>
    <div class="relative">
        <button
            type="button"
            class="relative rounded-full p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-zinc-800 transition-colors"
            :title="$t('app.language')"
            @click="toggleDropdown"
        >
            <MaterialDesignIcon icon-name="translate" class="w-6 h-6" />
        </button>

        <div
            v-if="isDropdownOpen"
            v-click-outside="closeDropdown"
            class="absolute right-0 mt-2 w-48 bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 rounded-2xl shadow-xl z-[9999] overflow-hidden"
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
    </div>
</template>

<script>
import MaterialDesignIcon from "./MaterialDesignIcon.vue";

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
            languages: [
                { code: "en", name: "English" },
                { code: "de", name: "Deutsch" },
                { code: "ru", name: "Русский" },
            ],
        };
    },
    computed: {
        currentLanguage() {
            return this.$i18n.locale;
        },
    },
    methods: {
        toggleDropdown() {
            this.isDropdownOpen = !this.isDropdownOpen;
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
