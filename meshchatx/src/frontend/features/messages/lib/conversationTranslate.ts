// SPDX-License-Identifier: 0BSD

export type LangOption = {
    value: string;
    label: string;
};

export type BubbleTranslation = {
    translatedText?: string;
    fromCode?: string;
    toCode?: string;
    showOriginal?: boolean;
    loading?: boolean;
};

export async function loadTranslatorLanguages(
    api: { get: (url: string, opts?: { params?: Record<string, unknown> }) => Promise<{ data?: unknown }> },
    libreUrl?: string
): Promise<{ languages: LangOption[]; hasTranslator: boolean }> {
    try {
        const params: Record<string, unknown> = {};
        if (libreUrl) {
            params.libretranslate_url = libreUrl;
        }
        const response = await api.get("/api/v1/translator/languages", { params });
        const data = response.data as
            { languages?: unknown[]; has_argos?: boolean; libretranslate_reachable?: boolean } | undefined;
        const list = Array.isArray(data?.languages) ? data.languages : [];
        const options: LangOption[] = list
            .map((item: unknown) => {
                if (typeof item === "string") {
                    return { value: item, label: item.toUpperCase() };
                }
                const obj = item as Record<string, unknown>;
                const code = String(obj.code || obj.value || "");
                const name = String(obj.name || obj.label || code);
                return { value: code, label: name };
            })
            .filter((opt: LangOption) => Boolean(opt.value));
        const hasTranslator = options.length > 0 || Boolean(data?.has_argos || data?.libretranslate_reachable);
        return { languages: options, hasTranslator };
    } catch {
        return { languages: [], hasTranslator: false };
    }
}

export async function translateText(
    api: { post: (url: string, body?: unknown) => Promise<{ data?: unknown }> },
    params: {
        text: string;
        targetLang: string;
        sourceLang?: string;
        useArgos?: boolean;
        libreUrl?: string;
        libreApiKey?: string;
    }
): Promise<{ translatedText: string; sourceLang: string }> {
    const payload: Record<string, unknown> = {
        text: params.text,
        target_lang: params.targetLang,
        source_lang: params.sourceLang || "auto",
        use_argos: Boolean(params.useArgos),
    };
    if (params.libreUrl) {
        payload.libretranslate_url = params.libreUrl;
    }
    if (params.libreApiKey) {
        payload.libretranslate_api_key = params.libreApiKey;
    }
    const response = await api.post("/api/v1/translator/translate", payload);
    const data = (response.data as { translated_text?: string; source_lang?: string } | undefined) || {};
    return {
        translatedText: String(data.translated_text || ""),
        sourceLang: String(data.source_lang || params.sourceLang || "auto"),
    };
}
