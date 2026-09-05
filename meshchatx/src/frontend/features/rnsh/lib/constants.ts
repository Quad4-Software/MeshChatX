// SPDX-License-Identifier: 0BSD

import type { RemoteShellTab } from "../../remote-shell/lib/types.js";
import type { RnshConnectForm, RnshListenForm } from "./types.js";

export const RNSH_VIEW_TABS: RemoteShellTab[] = [
    {
        id: "sessions",
        label: "rnsh.tab_sessions",
        shortLabel: "rnsh.tab_sessions_short",
        icon: "console-line",
    },
    {
        id: "connect",
        label: "rnsh.tab_connect",
        shortLabel: "rnsh.tab_connect_short",
        icon: "lan-connect",
    },
    {
        id: "listen",
        label: "rnsh.tab_listen",
        shortLabel: "rnsh.tab_listen_short",
        icon: "access-point-network",
    },
];

export const DEFAULT_RNSH_CONNECT_FORM: RnshConnectForm = {
    name: "",
    destination: "",
    command: "",
    config_path: "",
    mirror: false,
    no_id: false,
};

export const DEFAULT_RNSH_LISTEN_FORM: RnshListenForm = {
    name: "",
    allowed_hashes_text: "",
    command: "",
    config_path: "",
    no_auth: false,
};
