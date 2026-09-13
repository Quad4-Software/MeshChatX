// SPDX-License-Identifier: 0BSD

import type { TranslationPack } from "../../../js/TranslationService.js";

export type { TranslationPack };

export interface LanguageOption {
    value: string;
    label: string;
}

export interface InstalledPair {
    pair: string;
    from: string;
    to: string;
}
