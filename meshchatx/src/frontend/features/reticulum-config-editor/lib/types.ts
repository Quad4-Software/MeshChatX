// SPDX-License-Identifier: 0BSD

export type ReticulumConfigRawResponse = {
    content?: string;
    path?: string;
    message?: string;
    error?: string;
};

export type ReticulumConfigResetResponse = {
    content?: string;
    path?: string;
    message?: string;
    error?: string;
};

export type ReticulumReloadResponse = {
    message?: string;
    error?: string;
};

export type TabInsertionResult = {
    content: string;
    newCursor: number;
};
