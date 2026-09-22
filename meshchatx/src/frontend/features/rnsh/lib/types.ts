// SPDX-License-Identifier: 0BSD

import type { RemoteShellSession } from "../../remote-shell/lib/types.js";

export type RnshSession = RemoteShellSession;

export type RnshTabId = "sessions" | "connect" | "listen";

export interface RnshConnectForm {
    name: string;
    destination: string;
    command: string;
    config_path: string;
    mirror: boolean;
    no_id: boolean;
}

export interface RnshListenForm {
    name: string;
    allowed_hashes_text: string;
    command: string;
    config_path: string;
    no_auth: boolean;
}

export interface RnshConnectPayload {
    name?: string;
    mode: "connect";
    destination: string;
    remote_command?: string;
    config_path?: string;
    mirror: boolean;
    no_id: boolean;
    autostart: boolean;
}

export interface RnshListenPayload {
    name?: string;
    mode: "listen";
    allowed_hashes: string[];
    default_command?: string;
    config_path?: string;
    no_auth: boolean;
    autostart: boolean;
}
