// SPDX-License-Identifier: 0BSD

import DialogUtils from "../../../js/DialogUtils.js";
import ToastUtils from "../../../js/ToastUtils.js";
import GlobalEmitter from "../../../js/GlobalEmitter.js";
import { t } from "../../../js/i18n.js";
import type { NomadNode } from "./types.js";

export async function blockNodeDestination(node: NomadNode): Promise<void> {
    if (!(await DialogUtils.confirm(t("nomadnet.block_node_confirm", { name: node.display_name })))) {
        return;
    }
    try {
        if ((window as any).api) {
            await (window as any).api.post("/api/v1/blocked-destinations", {
                destination_hash: node.identity_hash || node.destination_hash,
            });
        }
        GlobalEmitter.emit("block-status-changed");
        DialogUtils.alert(t("nomadnet.node_blocked_successfully"));
    } catch (e) {
        DialogUtils.alert(t("nomadnet.failed_to_block_node"));
        console.error(e);
    }
}

export async function unblockNodeDestination(identityHash?: string): Promise<void> {
    if (!identityHash) return;
    try {
        if ((window as any).api) {
            await (window as any).api.delete(`/api/v1/blocked-destinations/${identityHash}`);
        }
        GlobalEmitter.emit("block-status-changed");
        DialogUtils.alert(t("nomadnet.banishment_lifted"));
    } catch (e) {
        DialogUtils.alert(t("nomadnet.failed_lift_banishment"));
        console.error(e);
    }
}

export async function bulkBlockNodeDestinations(targetNodes: NomadNode[]): Promise<boolean> {
    if (targetNodes.length === 0) return false;
    if (!(await DialogUtils.confirm(t("nomadnet.bulk_block_confirm", { count: targetNodes.length })))) {
        return false;
    }
    try {
        for (const n of targetNodes) {
            if ((window as any).api) {
                await (window as any).api.post("/api/v1/blocked-destinations", {
                    destination_hash: n.identity_hash || n.destination_hash,
                });
            }
        }
        GlobalEmitter.emit("block-status-changed");
        ToastUtils.success(t("nomadnet.bulk_block_done", { count: targetNodes.length }));
        return true;
    } catch (e) {
        DialogUtils.alert(t("nomadnet.failed_to_block_node"));
        console.error(e);
        return false;
    }
}
