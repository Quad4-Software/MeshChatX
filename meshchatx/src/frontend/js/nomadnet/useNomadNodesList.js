// @ts-check
// SPDX-License-Identifier: 0BSD

import { ref } from "vue";

import * as announcesApi from "../api/announces.js";

/**
 * Sidebar node-list state for NomadNetworkPage: announce list fetching,
 * debounced search, "load more" pagination, and per-request abort
 * handling. Each non-append fetch aborts the previous in-flight request
 * and only the latest request is allowed to clear isSearchingNodes.
 */
export function useNomadNodesList() {
    const nodes = ref({});
    const totalNodesCount = ref(0);
    const hasMoreNodes = ref(true);
    const isLoadingMoreNodes = ref(false);
    const isSearchingNodes = ref(false);
    const nodesSearchTerm = ref("");
    const pageSize = ref(50);
    const nodesRefreshTimeout = ref(null);
    const nodesListAbortController = ref(null);

    function updateNodeFromAnnounce(announce) {
        nodes.value[announce.destination_hash] = announce;
    }

    async function getNomadnetworkNodeAnnounces(append = false) {
        // capture the controller that belongs to *this* call so a later,
        // superseding call can't have its own finally block clear the
        // loading state for an in-flight search out from under it.
        let myController = nodesListAbortController.value;
        try {
            if (!append) {
                if (nodesListAbortController.value) {
                    nodesListAbortController.value.abort();
                }
                nodesListAbortController.value = new AbortController();
                myController = nodesListAbortController.value;
                isSearchingNodes.value = true;
            } else if (!nodesListAbortController.value) {
                nodesListAbortController.value = new AbortController();
                myController = nodesListAbortController.value;
            }
            const offset = append ? Object.keys(nodes.value).length : 0;
            const response = await announcesApi.listAnnounces({
                params: {
                    aspect: "nomadnetwork.node",
                    limit: pageSize.value,
                    offset: offset,
                    search: nodesSearchTerm.value,
                },
                signal: myController.signal,
            });

            const nodeAnnounces = response.data.announces;
            if (!append) {
                nodes.value = {};
            }

            totalNodesCount.value = response.data.total_count || 0;

            for (const nodeAnnounce of nodeAnnounces) {
                updateNodeFromAnnounce(nodeAnnounce);
            }

            hasMoreNodes.value = nodeAnnounces.length === pageSize.value;
        } catch (e) {
            if (window.api.isCancel?.(e)) return;
            console.log(e);
        } finally {
            isLoadingMoreNodes.value = false;
            if (!append && nodesListAbortController.value === myController) {
                isSearchingNodes.value = false;
            }
        }
    }

    async function loadMoreNodes() {
        if (isLoadingMoreNodes.value || !hasMoreNodes.value) return;
        isLoadingMoreNodes.value = true;
        await getNomadnetworkNodeAnnounces(true);
    }

    function onNodesSearchChanged(term) {
        nodesSearchTerm.value = term;
        isSearchingNodes.value = true;
        if (nodesRefreshTimeout.value) {
            clearTimeout(nodesRefreshTimeout.value);
        }
        nodesRefreshTimeout.value = setTimeout(() => {
            getNomadnetworkNodeAnnounces();
        }, 500);
    }

    return {
        nodes,
        totalNodesCount,
        hasMoreNodes,
        isLoadingMoreNodes,
        isSearchingNodes,
        nodesSearchTerm,
        pageSize,
        nodesRefreshTimeout,
        nodesListAbortController,
        updateNodeFromAnnounce,
        getNomadnetworkNodeAnnounces,
        loadMoreNodes,
        onNodesSearchChanged,
    };
}
