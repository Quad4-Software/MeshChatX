// SPDX-License-Identifier: 0BSD

export const RETICULUM_CONFIG_RAW_ENDPOINT = "/api/v1/reticulum/config/raw";
export const RETICULUM_CONFIG_RESET_ENDPOINT = "/api/v1/reticulum/config/reset";
export const RETICULUM_CONFIG_VERSIONS_ENDPOINT = "/api/v1/reticulum/config/versions";
export const RETICULUM_RELOAD_ENDPOINT = "/api/v1/reticulum/reload";

export function reticulumConfigVersionEndpoint(versionId: string): string {
    return `${RETICULUM_CONFIG_VERSIONS_ENDPOINT}/${encodeURIComponent(versionId)}`;
}

export function reticulumConfigVersionRestoreEndpoint(versionId: string): string {
    return `${reticulumConfigVersionEndpoint(versionId)}/restore`;
}

export const TOAST_ID_CONFIG_SAVE = "rns-config-save";
export const TOAST_ID_CONFIG_RESTORE = "rns-config-restore";
export const TOAST_ID_CONFIG_RELOAD = "rns-config-reload";

export const DEFAULT_TAB_INDENT = "  ";

export const RETICULUM_CONFIG_EDITOR_FEATURE_ID = "reticulum-config-editor";
export const RETICULUM_CONFIG_EDITOR_ROUTE_NAME = "reticulum-config-editor";
export const RETICULUM_CONFIG_EDITOR_ROUTE_PATH = "/tools/reticulum-config-editor";
