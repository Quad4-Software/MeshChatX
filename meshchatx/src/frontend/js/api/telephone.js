// @ts-check

/**
 * Endpoint wrappers for /api/v1/telephone.
 * Each function maps one HTTP call through window.api. Add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants";

export function listContacts(...rest) {
    return window.api.get(apiPath("/telephone/contacts"), ...rest);
}
export function listRecordings(...rest) {
    return window.api.get(apiPath("/telephone/recordings"), ...rest);
}
export function listVoicemails(...rest) {
    return window.api.get(apiPath("/telephone/voicemails"), ...rest);
}
export function uploadRingtones(data, ...rest) {
    return window.api.post(apiPath("/telephone/ringtones/upload"), data, ...rest);
}
export function uploadVoicemailGreeting(data, ...rest) {
    return window.api.post(apiPath("/telephone/voicemail/greeting/upload"), data, ...rest);
}
