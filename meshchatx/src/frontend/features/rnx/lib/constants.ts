// SPDX-License-Identifier: 0BSD

import type { RemoteShellTab } from "../../remote-shell/lib/types.js";
import type { RnxExecuteForm, RnxListenForm } from "./types.js";

export const RNX_VIEW_TABS: RemoteShellTab[] = [
    {
        id: "sessions",
        label: "rnx.tab_sessions",
        shortLabel: "rnx.tab_sessions_short",
        icon: "console-line",
    },
    {
        id: "execute",
        label: "rnx.tab_execute",
        shortLabel: "rnx.tab_execute_short",
        icon: "lan-connect",
    },
    {
        id: "listen",
        label: "rnx.tab_listen",
        shortLabel: "rnx.tab_listen_short",
        icon: "access-point-network",
    },
];

export const DEFAULT_RNX_EXECUTE_FORM: RnxExecuteForm = {
    name: "",
    destination: "",
    command: "",
    config_path: "",
    mirror: false,
    no_id: false,
    detailed: true,
    interactive: false,
    timeout: "",
    result_timeout: "",
    stdout_limit: "",
    stderr_limit: "",
};

export const DEFAULT_RNX_LISTEN_FORM: RnxListenForm = {
    name: "",
    allowed_hashes_text: "",
    config_path: "",
    no_auth: false,
};
