// SPDX-License-Identifier: 0BSD

export type TranslationMode = "argos" | "libretranslate";

export interface TranslatorLanguage {
    code: string;
    name: string;
    source: "argos" | "libretranslate";
}

export interface TranslatorConfig {
    translator_argos_enabled?: boolean;
    translator_libretranslate_enabled?: boolean;
    libretranslate_url?: string | null;
    libretranslate_api_key?: string | null;
    [key: string]: unknown;
}

export interface TranslationResult {
    translated_text: string;
    source: string;
    source_lang: string;
    target_lang: string;
}

export interface TranslatorLanguagesResponse {
    languages?: TranslatorLanguage[];
    has_argos?: boolean;
    has_argos_lib?: boolean;
    has_argos_cli?: boolean;
    libre_client_available?: boolean;
    libretranslate_reachable?: boolean;
}
