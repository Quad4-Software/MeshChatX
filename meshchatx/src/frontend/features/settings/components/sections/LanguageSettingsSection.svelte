<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { listLocaleCodes } from "../../../../js/localeLoader.js";
    import { t } from "../../../../js/i18n.js";

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

    const languages = listLocaleCodes().map((code) => ({
        code,
        name: LANGUAGE_NAMES[code] || code,
    }));

    interface Props {
        visible?: boolean;
        language?: string;
        onchange?: (lang: string) => void;
    }

    let { visible = true, language = "en", onchange }: Props = $props();
</script>

{#if visible}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">i18n</div>
                <h2>{t("app.language")}</h2>
                <p>{t("app.select_language")}</p>
            </div>
        </header>
        <div class="settings-section__body space-y-3">
            <label for="language-select" class="sr-only">{t("app.language")}</label>
            <select
                id="language-select"
                value={language}
                class="input-field"
                onchange={(e) => onchange?.((e.target as HTMLSelectElement).value)}
            >
                {#each languages as lang (lang.code)}
                    <option value={lang.code}>
                        {lang.name}
                    </option>
                {/each}
            </select>
        </div>
    </section>
{/if}
