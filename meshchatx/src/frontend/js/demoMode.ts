// SPDX-License-Identifier: 0BSD

export function isDemoReadonly(status) {
    return Boolean(status && status.demo_mode === true);
}
