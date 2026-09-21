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

export type ReticulumConfigVersion = {
    id: string;
    created_at?: string;
    label?: string;
    size?: number;
};

export type ReticulumConfigVersionsResponse = {
    versions?: ReticulumConfigVersion[];
    error?: string;
};

export type ReticulumConfigVersionResponse = {
    version?: ReticulumConfigVersion & { content?: string };
    error?: string;
};

export type TabInsertionResult = {
    content: string;
    newCursor: number;
};
