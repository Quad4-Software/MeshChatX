// SPDX-License-Identifier: 0BSD

export function isDemoReadonly(status) {
    return Boolean(status && status.demo_mode === true);
}

export function isAltchaEnabled(status) {
    return Boolean(status && status.altcha_enabled === true);
}
