// @ts-check

/**
 * Endpoint wrappers for /api/v1/app.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function getChangelog(...rest) {
    return window.api.get(apiPath("/app/changelog"), ...rest);
}
export function getInfo(...rest) {
    return window.api.get(apiPath("/app/info"), ...rest);
}
export function listSessions(...rest) {
    return window.api.get(apiPath("/app/sessions"), ...rest);
}
export function seenChangelog(data, ...rest) {
    return window.api.post(apiPath("/app/changelog/seen"), data, ...rest);
}
export function seenChannelPrompt(data, ...rest) {
    return window.api.post(apiPath("/app/channel-prompt/seen"), data, ...rest);
}
export function acknowledgeIntegrity(data, ...rest) {
    return window.api.post(apiPath("/app/integrity/acknowledge"), data, ...rest);
}
export function shutdownApp(data, ...rest) {
    return window.api.post(apiPath("/app/shutdown"), data, ...rest);
}
export function seenTutorial(data, ...rest) {
    return window.api.post(apiPath("/app/tutorial/seen"), data, ...rest);
}
