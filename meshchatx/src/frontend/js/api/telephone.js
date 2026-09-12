// @ts-check

/**
 * Endpoint wrappers for /api/v1/telephone.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function deleteContacts(contactId, ...rest) {
    return window.api.delete(apiPath(`/telephone/contacts/${contactId}`), ...rest);
}
export function deleteContacts2(id, ...rest) {
    return window.api.delete(apiPath(`/telephone/contacts/${id}`), ...rest);
}
export function deleteHistory(...rest) {
    return window.api.delete(apiPath("/telephone/history"), ...rest);
}
export function deleteRecordings(recordingId, ...rest) {
    return window.api.delete(apiPath(`/telephone/recordings/${recordingId}`), ...rest);
}
export function deleteRingtones(id, ...rest) {
    return window.api.delete(apiPath(`/telephone/ringtones/${id}`), ...rest);
}
export function deleteVoicemailGreeting(...rest) {
    return window.api.delete(apiPath("/telephone/voicemail/greeting"), ...rest);
}
export function deleteVoicemails(voicemailId, ...rest) {
    return window.api.delete(apiPath(`/telephone/voicemails/${voicemailId}`), ...rest);
}
export function listAudioProfiles(...rest) {
    return window.api.get(apiPath("/telephone/audio-profiles"), ...rest);
}
export function listCallModes(...rest) {
    return window.api.get(apiPath("/telephone/call-modes"), ...rest);
}
export function listContacts(...rest) {
    return window.api.get(apiPath("/telephone/contacts"), ...rest);
}
export function getContactsCheck(destinationHash, ...rest) {
    return window.api.get(apiPath(`/telephone/contacts/check/${destinationHash}`), ...rest);
}
export function getContactsCheck2(hash, ...rest) {
    return window.api.get(apiPath(`/telephone/contacts/check/${hash}`), ...rest);
}
export function getContactsCheck3(destinationHash, ...rest) {
    return window.api.get(apiPath(`/telephone/contacts/check/${destinationHash}`), ...rest);
}
export function getContactsCheck4(destinationHash, ...rest) {
    return window.api.get(apiPath(`/telephone/contacts/check/${destinationHash}`), ...rest);
}
export function getContactsExport(...rest) {
    return window.api.get(apiPath("/telephone/contacts/export"), ...rest);
}
export function getHistory(callHistoryLimit, callHistoryOffset, ...rest) {
    return window.api.get(apiPath(`/telephone/history?limit=${callHistoryLimit}&offset=${callHistoryOffset}`), ...rest);
}
export function listRecordings(...rest) {
    return window.api.get(apiPath("/telephone/recordings"), ...rest);
}
export function listRingtones(...rest) {
    return window.api.get(apiPath("/telephone/ringtones"), ...rest);
}
export function getRingtonesStatus(...rest) {
    return window.api.get(apiPath("/telephone/ringtones/status"), ...rest);
}
export function getRingtonesStatusForCaller(callerHash, ...rest) {
    return window.api.get(apiPath(`/telephone/ringtones/status?caller_hash=${callerHash}`), ...rest);
}
export function getStatus(...rest) {
    return window.api.get(apiPath("/telephone/status"), ...rest);
}
export function getVoicemailStatus(...rest) {
    return window.api.get(apiPath("/telephone/voicemail/status"), ...rest);
}
export function listVoicemails(...rest) {
    return window.api.get(apiPath("/telephone/voicemails"), ...rest);
}
export function updateContacts(id, data, ...rest) {
    return window.api.patch(apiPath(`/telephone/contacts/${id}`), data, ...rest);
}
export function updateContacts2(contactId, data, ...rest) {
    return window.api.patch(apiPath(`/telephone/contacts/${contactId}`), data, ...rest);
}
export function updateContacts3(id, data, ...rest) {
    return window.api.patch(apiPath(`/telephone/contacts/${id}`), data, ...rest);
}
export function updateContacts4(id, data, ...rest) {
    return window.api.patch(apiPath(`/telephone/contacts/${id}`), data, ...rest);
}
export function updateContacts5(id, data, ...rest) {
    return window.api.patch(apiPath(`/telephone/contacts/${id}`), data, ...rest);
}
export function updateRingtones(id, data, ...rest) {
    return window.api.patch(apiPath(`/telephone/ringtones/${id}`), data, ...rest);
}
export function updateRingtones2(editingRingtoneId, data, ...rest) {
    return window.api.patch(apiPath(`/telephone/ringtones/${editingRingtoneId}`), data, ...rest);
}
export function postAnswer(data, ...rest) {
    return window.api.post(apiPath("/telephone/answer"), data, ...rest);
}
export function postCall(hashToCall, data, ...rest) {
    return window.api.post(apiPath(`/telephone/call/${hashToCall}`), data, ...rest);
}
export function postCall2(hash, data, ...rest) {
    return window.api.post(apiPath(`/telephone/call/${hash}`), data, ...rest);
}
export function postCall3(destinationHash, data, ...rest) {
    return window.api.post(apiPath(`/telephone/call/${destinationHash}`), data, ...rest);
}
export function createContacts(data, ...rest) {
    return window.api.post(apiPath("/telephone/contacts"), data, ...rest);
}
export function importContacts(data, ...rest) {
    return window.api.post(apiPath("/telephone/contacts/import"), data, ...rest);
}
export function postHangup(data, ...rest) {
    return window.api.post(apiPath("/telephone/hangup"), data, ...rest);
}
export function postMissedCallsMarkViewed(data, ...rest) {
    return window.api.post(apiPath("/telephone/missed-calls/mark-viewed"), data, ...rest);
}
export function postPtt(data, ...rest) {
    return window.api.post(apiPath("/telephone/ptt"), data, ...rest);
}
export function uploadRingtones(data, ...rest) {
    return window.api.post(apiPath("/telephone/ringtones/upload"), data, ...rest);
}
export function postSendToVoicemail(data, ...rest) {
    return window.api.post(apiPath("/telephone/send-to-voicemail"), data, ...rest);
}
export function postSwitchAudioProfile(audioProfileId, data, ...rest) {
    return window.api.post(apiPath(`/telephone/switch-audio-profile/${audioProfileId}`), data, ...rest);
}
export function postSwitchCallMode(modeId, data, ...rest) {
    return window.api.post(apiPath(`/telephone/switch-call-mode/${modeId}`), data, ...rest);
}
export function postSwitchCallMode2(nextMode, data, ...rest) {
    return window.api.post(apiPath(`/telephone/switch-call-mode/${nextMode}`), data, ...rest);
}
export function postVoicemailGenerateGreeting(data, ...rest) {
    return window.api.post(apiPath("/telephone/voicemail/generate-greeting"), data, ...rest);
}
export function startVoicemailGreetingRecord(data, ...rest) {
    return window.api.post(apiPath("/telephone/voicemail/greeting/record/start"), data, ...rest);
}
export function stopVoicemailGreetingRecord(data, ...rest) {
    return window.api.post(apiPath("/telephone/voicemail/greeting/record/stop"), data, ...rest);
}
export function uploadVoicemailGreeting(data, ...rest) {
    return window.api.post(apiPath("/telephone/voicemail/greeting/upload"), data, ...rest);
}
export function postVoicemailsRead(id, data, ...rest) {
    return window.api.post(apiPath(`/telephone/voicemails/${id}/read`), data, ...rest);
}
