// SPDX-License-Identifier: 0BSD

import type { RemoteShellSession } from "../../remote-shell/lib/types.js";

export type RnxSession = RemoteShellSession;

export type RnxTabId = "sessions" | "execute" | "listen";

export interface RnxExecuteForm {
    name: string;
    destination: string;
    command: string;
    config_path: string;
    mirror: boolean;
    no_id: boolean;
    detailed: boolean;
    interactive: boolean;
    timeout: string | number;
    result_timeout: string | number;
    stdout_limit: string | number;
    stderr_limit: string | number;
}

export interface RnxListenForm {
    name: string;
    allowed_hashes_text: string;
    config_path: string;
    no_auth: boolean;
}

export interface RnxExecutePayload {
    name?: string;
    mode: "execute" | "interactive";
    destination: string;
    remote_command?: string;
    config_path?: string;
    mirror: boolean;
    no_id: boolean;
    detailed: boolean;
    timeout?: string;
    result_timeout?: string;
    stdout_limit?: string;
    stderr_limit?: string;
    autostart: boolean;
}

export interface RnxListenPayload {
    name?: string;
    mode: "listen";
    allowed_hashes: string[];
    config_path?: string;
    no_auth: boolean;
    autostart: boolean;
}
