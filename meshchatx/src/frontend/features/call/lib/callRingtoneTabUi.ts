// SPDX-License-Identifier: 0BSD

import DialogUtils from "../../../js/DialogUtils.js";
import { t } from "../../../js/i18n.js";
import ToastUtils from "../../../js/ToastUtils.js";
import { deleteRingtone, patchRingtone, uploadRingtone } from "./callApi.js";
import type { Ringtone, RingtoneStatus, TelephoneConfig } from "./types.js";
import type { RingtoneItem } from "./ringtoneEditorLogic.js";

export interface RingtoneConfig {
    custom_ringtone_enabled?: boolean;
    ringtone_volume?: number;
    telephone_tone_generator_enabled?: boolean;
    telephone_tone_generator_volume?: number;
    ringtone_preferred_id?: number | null;
    [key: string]: unknown;
}

export interface RingtoneStatusState {
    has_custom_ringtone?: boolean;
    enabled?: boolean;
    filename?: string | null;
    id?: number | null;
    volume?: number;
    [key: string]: unknown;
}

export interface CallRingtoneTabProps {
    active?: boolean;
    config?: RingtoneConfig | TelephoneConfig | Record<string, any> | null;
    ringtones?: RingtoneItem[] | Ringtone[];
    ringtoneStatus?: RingtoneStatusState | RingtoneStatus | Record<string, any>;
    isRingtoneEditorOpen?: boolean;
    editingRingtoneForAudio?: RingtoneItem | Ringtone | Record<string, any> | null;
    isUploadingRingtone?: boolean;
    isPlayingRingtone?: boolean;
    playingRingtoneId?: number | string | null;
    editingRingtoneId?: number | string | null;
    editingRingtoneName?: string;
    formatDestinationHash?: (hash?: string) => string;
    onupdateconfig?: (patch: Record<string, unknown>) => void;
    onopeneditor?: (ringtone: Ringtone | RingtoneItem) => void;
    oncloseeditor?: () => void;
    onringtonesaved?: () => void;
    onupload?: (event: Event, file?: File) => void;
    onplay?: (ringtone: Ringtone | RingtoneItem) => void;
    ondelete?: (ringtone: Ringtone | RingtoneItem) => void;
    onsetdefault?: (ringtone: Ringtone | RingtoneItem) => void;
    onsetprimary?: (ringtone: Ringtone | RingtoneItem) => void;
    onrename?: (ringtoneId: number | string, name: string) => void;
    onstartrename?: (ringtone: Ringtone | RingtoneItem) => void;
    onrenameinput?: (name: string) => void;
    oncopy?: (text: string) => void;
}

/**
 * Returns audio endpoint URL for a given ringtone
 */
export function getRingtoneAudioSrc(ringtoneId: number | string, download = false): string {
    const cleanId = encodeURIComponent(String(ringtoneId));
    return `/api/v1/telephone/ringtones/${cleanId}/audio${download ? "?download=1" : ""}`;
}

/**
 * Updates ringtone display name
 */
export async function executeSaveRingtoneName(ringtoneId: number | string, displayName: string): Promise<boolean> {
    try {
        await patchRingtone(ringtoneId, { display_name: displayName });
        return true;
    } catch (e) {
        console.error(e);
        ToastUtils.error(t("call.failed_to_update_ringtone_name"));
        return false;
    }
}

/**
 * Sets a ringtone as primary
 */
export async function executeSetPrimaryRingtone(ringtoneId: number | string): Promise<boolean> {
    try {
        await patchRingtone(ringtoneId, { is_primary: true });
        ToastUtils.success(t("call.primary_ringtone_set"));
        return true;
    } catch (e) {
        console.error(e);
        ToastUtils.error(t("call.failed_to_set_primary_ringtone"));
        return false;
    }
}

/**
 * Confirms and deletes a ringtone
 */
export async function executeDeleteRingtone(ringtoneId: number | string): Promise<boolean> {
    const confirmed = await DialogUtils.confirm(t("common.delete_confirm"));
    if (!confirmed) return false;
    try {
        await deleteRingtone(ringtoneId);
        ToastUtils.success(t("call.ringtone_deleted"));
        return true;
    } catch (e) {
        console.error(e);
        ToastUtils.error(t("call.failed_to_delete_ringtone"));
        return false;
    }
}

/**
 * Uploads a ringtone file
 */
export async function executeUploadRingtoneFile(file: File): Promise<boolean> {
    const formData = new FormData();
    formData.append("file", file);
    try {
        await uploadRingtone(formData);
        ToastUtils.success(t("call.ringtone_uploaded_successfully"));
        return true;
    } catch (e: any) {
        console.error(e);
        ToastUtils.error(e?.response?.data?.message || t("call.failed_to_upload_ringtone"));
        return false;
    }
}
