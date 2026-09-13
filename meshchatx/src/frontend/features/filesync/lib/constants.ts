// SPDX-License-Identifier: 0BSD

import type { FilesyncTabId } from "./types.js";

export const FILESYNC_TABS: { id: FilesyncTabId; labelKey: string }[] = [
    { id: "folder", labelKey: "rns_filesync.tab_folder" },
    { id: "devices", labelKey: "rns_filesync.tab_devices" },
    { id: "files", labelKey: "rns_filesync.tab_files" },
    { id: "remote", labelKey: "rns_filesync.tab_remote" },
    { id: "sharing", labelKey: "rns_filesync.tab_sharing" },
];
