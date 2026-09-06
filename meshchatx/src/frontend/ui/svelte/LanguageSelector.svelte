<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, tick } from "svelte";
    import { t } from "../../js/i18n.js";
    import { clampFloatingToViewport } from "../../js/clampFloatingToViewport.js";
    import { ensureLocaleMessages, getCurrentUiLocale, listLocaleCodes, setLocale } from "../../js/localeLoader.js";
    import MaterialDesignIcon from "./MaterialDesignIcon.svelte";

    interface Props {
        class?: string;
        onlanguagechange?: (code: string) => void;
    }

    let { class: className = "", onlanguagechange }: Props = $props();

    const LANGUAGE_NAMES: Record<string, string> = {
        de: "Deutsch",
        en: "English",
        es: "Español",
        fi: "Suomi",
        fr: "Français",
        it: "Italiano",
        ja: "日本語",
        ko: "한국어",
        nl: "Nederlands",
        pl: "Polski",
        "pt-br": "Português (Brasil)",
        ru: "Русский",
        tr: "Türkçe",
        uk: "Українська",
        zh: "中文",
    };

    const discoveredLanguages = listLocaleCodes().map((code) => ({
        code,
        name: LANGUAGE_NAMES[code] || code,
    }));

    let isDropdownOpen = $state(false);
    let dropdownPosition = $state({ top: 0, left: 0 });
    let dropdownMaxHeight = $state<number | null>(null);
    let currentLanguage = $state(getCurrentUiLocale() || "en");
    let dropdownPanel: HTMLElement | undefined = $state();
    let triggerButton: HTMLButtonElement | undefined = $state();

    const dropdownStyle = $derived(
        `top: ${dropdownPosition.top}px; left: ${dropdownPosition.left}px; ${
            dropdownMaxHeight != null ? `max-height: ${dropdownMaxHeight}px; overflow-y: auto;` : "overflow: hidden;"
        }`
    );

    function updateDropdownPosition(target: HTMLElement): void {
        const rect = target.getBoundingClientRect();
        dropdownMaxHeight = null;
        dropdownPosition = {
            top: rect.bottom + 8,
            left: Math.max(8, rect.right - 192),
        };
        void tick().then(() => {
            if (!dropdownPanel) return;
            const pr = dropdownPanel.getBoundingClientRect();
            const { left, top, maxHeight } = clampFloatingToViewport(pr.left, pr.top, pr.width, pr.height);
            dropdownPosition = { left, top };
            dropdownMaxHeight = maxHeight;
        });
    }

    function toggleDropdown(event: MouseEvent): void {
        isDropdownOpen = !isDropdownOpen;
        if (isDropdownOpen) {
            updateDropdownPosition(event.currentTarget as HTMLElement);
        }
    }

    function closeDropdown(): void {
        isDropdownOpen = false;
    }

    async function selectLanguage(langCode: string): Promise<void> {
        if (currentLanguage === langCode) {
            closeDropdown();
            return;
        }

        try {
            const ok = await setLocale(undefined, langCode);
            if (!ok) {
                await ensureLocaleMessages(undefined, langCode);
            }
            currentLanguage = langCode;
        } catch {
            /* locale pack may be unavailable */
        }
        onlanguagechange?.(langCode);
        closeDropdown();
    }

    function onDocumentClick(event: MouseEvent): void {
        if (!isDropdownOpen) return;
        const target = event.target as Node | null;
        if (dropdownPanel && !dropdownPanel.contains(target) && triggerButton && !triggerButton.contains(target)) {
            closeDropdown();
        }
    }

    onMount(() => {
        document.addEventListener("click", onDocumentClick);
        return () => {
            document.removeEventListener("click", onDocumentClick);
        };
    });
</script>

<div class="relative inline-block {className}">
    <button
        bind:this={triggerButton}
        type="button"
        class="relative rounded-full p-1.5 sm:p-2 text-sem-fg-muted hover:bg-sem-surface-muted transition-colors"
        title={t("app.language")}
        aria-label={t("app.language")}
        onclick={toggleDropdown}
    >
        <MaterialDesignIcon iconName="translate" class="w-5 h-5 sm:w-6 sm:h-6" />
    </button>

    {#if isDropdownOpen}
        <div
            bind:this={dropdownPanel}
            class="fixed w-48 bg-sem-surface border border-sem-border rounded-2xl shadow-xl z-9999 overflow-x-hidden"
            style={dropdownStyle}
            role="menu"
        >
            <div class="p-2">
                {#each discoveredLanguages as lang (lang.code)}
                    <button
                        type="button"
                        class="w-full px-4 py-2 text-left rounded-lg hover:bg-sem-surface-muted transition-colors flex items-center justify-between {currentLanguage ===
                        lang.code
                            ? 'bg-sem-surface-muted text-sem-accent'
                            : 'text-sem-fg'}"
                        onclick={() => selectLanguage(lang.code)}
                    >
                        <span class="font-medium">{lang.name}</span>
                        {#if currentLanguage === lang.code}
                            <MaterialDesignIcon iconName="check" class="w-5 h-5" />
                        {/if}
                    </button>
                {/each}
            </div>
        </div>
    {/if}
</div>
