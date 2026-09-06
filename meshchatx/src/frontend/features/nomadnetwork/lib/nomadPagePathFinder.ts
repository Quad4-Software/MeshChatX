// SPDX-License-Identifier: 0BSD

import ToastUtils from "../../../js/ToastUtils.js";
import { runDestinationPathFinder } from "../../../js/reticulumPathfinding.js";
import { t } from "../../../js/i18n.js";

export type NomadPathFinderMode = "quick" | "force" | "drop_then_request";

export async function runNomadPathFinder(options: {
    destinationHash: string;
    mode: NomadPathFinderMode;
    onReload: () => void;
}): Promise<void> {
    const api = (window as any).api;
    if (!options.destinationHash || !api) return;
    try {
        if (options.mode === "quick") {
            await runDestinationPathFinder(api, options.destinationHash, "quick");
            ToastUtils.success(t("nomadnet.path_finder_request_sent"));
            options.onReload();
        } else if (options.mode === "force") {
            const { path } = await runDestinationPathFinder(api, options.destinationHash, "force", {
                forceTimeout: 15,
            });
            if (path) {
                ToastUtils.success(t("nomadnet.path_finder_found"));
                options.onReload();
            } else {
                ToastUtils.error(t("nomadnet.path_finder_not_found"));
            }
        } else {
            await runDestinationPathFinder(api, options.destinationHash, "drop_then_request", {
                onDropPathError: (e) => console.warn("drop-path failed (continuing)", e),
            });
            ToastUtils.success(t("nomadnet.path_finder_dropped_and_requested"));
            options.onReload();
        }
    } catch (e) {
        console.error("path finder failed", e);
        ToastUtils.error(t("nomadnet.path_finder_failed"));
    }
}
