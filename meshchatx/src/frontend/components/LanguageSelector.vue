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

<script setup lang="ts">
import { computed, getCurrentInstance, nextTick, ref } from "vue";
import MaterialDesignIcon from "./MaterialDesignIcon.vue";
import { clampFloatingToViewport } from "../js/clampFloatingToViewport.js";
import { ensureLocaleMessages, getUiI18n, listLocaleOptions, setLocale } from "../js/localeLoader.js";

const languageOptions = listLocaleOptions();

const emit = defineEmits<{
    "language-change": [langCode: string];
}>();

const vClickOutside = {
    mounted(el: any, binding: any) {
        el.clickOutsideEvent = function (event: Event) {
            if (!(el === event.target || el.contains(event.target))) {
                binding.value();
            }
        };
        document.addEventListener("click", el.clickOutsideEvent);
    },
    unmounted(el: any) {
        document.removeEventListener("click", el.clickOutsideEvent);
    },
};

const isDropdownOpen = ref(false);
const dropdownPosition = ref<{ top: number; left: number }>({ top: 0, left: 0 });
const dropdownMaxHeight = ref<number | null>(null);

const languageDropdown = ref<HTMLElement | null>(null);

const instance = getCurrentInstance();

function resolveI18n(): any {
    // In tests globalProperties.$i18n is mocked; in the app it is the vue-i18n
    // global injection proxying the same composer registerUiI18n holds.
    return (instance?.proxy as any)?.$i18n ?? getUiI18n();
}

const currentLanguage = computed(() => {
    const locale = resolveI18n()?.locale;
    if (locale && typeof locale === "object" && "value" in locale) {
        return locale.value;
    }
    return locale || "";
});

const languages = computed(() => languageOptions);

const dropdownStyle = computed(() => {
    const style: Record<string, string> = {
        top: `${dropdownPosition.value.top}px`,
        left: `${dropdownPosition.value.left}px`,
    };
    if (dropdownMaxHeight.value != null) {
        style.maxHeight = `${dropdownMaxHeight.value}px`;
        style.overflowY = "auto";
    } else {
        style.overflow = "hidden";
    }
    return style;
});

function toggleDropdown(event: MouseEvent) {
    isDropdownOpen.value = !isDropdownOpen.value;
    if (isDropdownOpen.value) {
        updateDropdownPosition(event);
    }
}

function updateDropdownPosition(event: MouseEvent) {
    const button = event.currentTarget as HTMLElement;
    const rect = button.getBoundingClientRect();
    dropdownMaxHeight.value = null;
    dropdownPosition.value = {
        top: rect.bottom + 8,
        left: Math.max(8, rect.right - 192),
    };
    nextTick(() => {
        const panel = languageDropdown.value;
        if (!panel) return;
        const pr = panel.getBoundingClientRect();
        const { left, top, maxHeight } = clampFloatingToViewport(pr.left, pr.top, pr.width, pr.height);
        dropdownPosition.value = { left, top };
        dropdownMaxHeight.value = maxHeight;
    });
}

function closeDropdown() {
    isDropdownOpen.value = false;
}

async function selectLanguage(langCode: string) {
    if (currentLanguage.value === langCode) {
        closeDropdown();
        return;
    }

    // Apply immediately. Parent persists config. The registered composer is the
    // same instance Options API this.$i18n proxies to.
    const i18n = resolveI18n();
    try {
        const ok = await setLocale(i18n, langCode);
        if (!ok) {
            await ensureLocaleMessages(i18n, langCode);
        }
    } catch {
        // Locale pack may be unavailable in tests or offline shells.
    }
    emit("language-change", langCode);
    closeDropdown();
}
</script>
