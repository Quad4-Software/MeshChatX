// SPDX-License-Identifier: 0BSD

import { DEFAULT_TAB_INDENT } from "./constants.js";
import type { TabInsertionResult } from "./types.js";

/**
 * Inserts tab spaces at the active selection range in text content.
 */
export function insertTabAtSelection(
    content: string,
    start: number,
    end: number,
    indent: string = DEFAULT_TAB_INDENT
): TabInsertionResult {
    const safeStart = Math.max(0, Math.min(start, content.length));
    const safeEnd = Math.max(safeStart, Math.min(end, content.length));
    const before = content.substring(0, safeStart);
    const after = content.substring(safeEnd);
    return {
        content: `${before}${indent}${after}`,
        newCursor: safeStart + indent.length,
    };
}

/**
 * Determines whether editor content has uncommitted changes compared to original content.
 */
export function isConfigDirty(content: string, originalContent: string): boolean {
    return content !== originalContent;
}

/**
 * Determines whether the restart reminder banner should be shown.
 */
export function shouldShowRestartReminder(
    hasSavedChanges: boolean,
    hasPendingInterfaceChanges: boolean
): boolean {
    return Boolean(hasSavedChanges || hasPendingInterfaceChanges);
}

/**
 * Extracts a human-readable error message from an API response or error object.
 */
export function extractErrorMessage(error: unknown, fallback: string): string {
    if (error && typeof error === "object") {
        const err = error as {
            response?: {
                data?: {
                    error?: string;
                    message?: string;
                };
            };
            message?: string;
        };
        return err.response?.data?.error || err.response?.data?.message || err.message || fallback;
    }
    if (typeof error === "string" && error.length > 0) {
        return error;
    }
    return fallback;
}
