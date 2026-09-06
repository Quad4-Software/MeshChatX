// SPDX-License-Identifier: 0BSD

import { AUTH_MIN_PASSWORD_LENGTH } from "./constants.js";

export interface AuthStatusPayload {
    auth_enabled?: boolean;
    authenticated?: boolean;
    password_set?: boolean;
    auth_page_hint?: string;
}

export interface AuthValidationResult {
    valid: boolean;
    errorKey?: string;
}

/**
 * Validate password requirements for setup and login
 */
export function validateAuthForm(isSetup: boolean, password: string, confirmPassword: string): AuthValidationResult {
    if (isSetup) {
        // Client form confirm-field equality, not secret verify
        // eslint-disable-next-line security/detect-possible-timing-attacks
        if (password !== confirmPassword) {
            return { valid: false, errorKey: "auth.passwords_mismatch" };
        }
        if (password.length < AUTH_MIN_PASSWORD_LENGTH) {
            return { valid: false, errorKey: "auth.password_min_length" };
        }
    }
    return { valid: true };
}
