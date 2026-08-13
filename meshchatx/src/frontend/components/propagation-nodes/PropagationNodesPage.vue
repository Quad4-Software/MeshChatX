<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas text-sem-fg">
        <ToolsPageHeader icon="mailbox" :title="$t('tools.propagation_nodes.title')" accent="cyan">
            <template #actions>
                <button
                    type="button"
                    class="inline-flex size-9 items-center justify-center rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted hover:text-sem-accent"
                    :title="$t('tools.propagation_nodes.reload')"
                    @click="loadPropagationNodes"
                >
                    <MaterialDesignIcon icon-name="refresh" class="size-5" />
                </button>
            </template>
        </ToolsPageHeader>

        <div class="shrink-0 border-b border-sem-border">
            <div class="flex items-center gap-2 px-3 py-1.5 min-h-10">
                <button
                    type="button"
                    class="flex min-w-0 flex-1 items-center gap-2 text-left"
                    data-testid="prop-nodes-hosted-toggle"
                    @click="isLocalManagerCollapsed = !isLocalManagerCollapsed"
                >
                    <MaterialDesignIcon
                        :icon-name="isLocalManagerCollapsed ? 'chevron-right' : 'chevron-down'"
                        class="size-4 text-sem-fg-muted shrink-0"
                    />
                    <span class="text-sm font-medium truncate">{{ $t("tools.propagation_nodes.hosted_heading") }}</span>
                    <span
                        v-if="localPropagationNode"
                        class="inline-flex items-center rounded-full px-1.5 py-0 text-[10px] font-semibold shrink-0"
                        :class="
                            localNodeIsRunning
                                ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                                : 'bg-sem-surface-muted text-sem-fg-muted'
                        "
                    >
                        {{
                            localNodeIsRunning
                                ? $t("tools.propagation_nodes.running")
                                : $t("tools.propagation_nodes.stopped")
                        }}
                    </span>
                    <span
                        v-if="
                            localPropagationNode &&
                            config.lxmf_preferred_propagation_node_destination_hash ===
                                localPropagationNode.destination_hash
                        "
                        class="inline-flex items-center rounded-full bg-blue-100 dark:bg-blue-900/30 px-1.5 py-0 text-[10px] font-semibold text-blue-700 dark:text-blue-300 shrink-0"
                    >
                        {{ $t("tools.propagation_nodes.preferred_badge") }}
                    </span>
                </button>
                <div class="flex items-center gap-0.5 shrink-0">
                    <button
                        type="button"
                        class="inline-flex size-8 items-center justify-center rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted hover:text-sem-accent disabled:opacity-40"
                        :title="$t('app.announce_now')"
                        :disabled="!localPropagationNode"
                        @click="announceNow"
                    >
                        <MaterialDesignIcon icon-name="bullhorn" class="size-4" />
                    </button>
                    <button
                        v-if="!localNodeIsRunning"
                        type="button"
                        class="inline-flex size-8 items-center justify-center rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted hover:text-emerald-600 disabled:opacity-40"
                        :title="$t('tools.propagation_nodes.start_node')"
                        :disabled="!localPropagationNode"
                        @click="startLocalPropagationNode"
                    >
                        <MaterialDesignIcon icon-name="play" class="size-4" />
                    </button>
                    <button
                        v-if="localNodeIsRunning"
                        type="button"
                        class="inline-flex size-8 items-center justify-center rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted hover:text-amber-600"
                        :title="$t('tools.propagation_nodes.restart_node')"
                        @click="restartLocalPropagationNode"
                    >
                        <MaterialDesignIcon icon-name="refresh" class="size-4" />
                    </button>
                    <button
                        v-if="localNodeIsRunning"
                        type="button"
                        class="inline-flex size-8 items-center justify-center rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted hover:text-red-600"
                        :title="$t('tools.propagation_nodes.stop_node')"
                        @click="stopLocalPropagationNode"
                    >
                        <MaterialDesignIcon icon-name="stop" class="size-4" />
                    </button>
                </div>
            </div>

            <div
                v-if="!isLocalManagerCollapsed"
                data-testid="prop-nodes-hosted-expanded"
                class="px-3 pb-3 space-y-2 border-t border-sem-border"
            >
                <div
                    v-if="config.lxmf_local_propagation_node_address_hash"
                    class="pt-2 text-[11px] font-mono text-sem-fg-muted break-all"
                >
                    {{ formatDestinationHash(config.lxmf_local_propagation_node_address_hash) }}
                </div>
                <div class="text-[11px] text-sem-fg-muted flex items-center gap-2">
                    <span>{{ formatPathLabel(nodePathFor(config.lxmf_local_propagation_node_address_hash)) }}</span>
                    <button
                        type="button"
                        class="inline-flex size-7 items-center justify-center rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted hover:text-sem-accent disabled:opacity-40"
                        :title="$t('tools.propagation_nodes.find_path')"
                        :disabled="!config.lxmf_local_propagation_node_address_hash"
                        @click="requestPathForNode(config.lxmf_local_propagation_node_address_hash)"
                    >
                        <MaterialDesignIcon icon-name="map-marker-path" class="size-4" />
                    </button>
                </div>
                <label class="block text-[11px] text-sem-fg-muted">
                    {{ $t("tools.propagation_nodes.display_name") }}
                    <div class="mt-1 flex items-center gap-2">
                        <input
                            v-model.trim="localNodeDisplayNameDraft"
                            type="text"
                            maxlength="64"
                            class="input-field py-1.5 text-sm"
                            :placeholder="$t('tools.propagation_nodes.display_name')"
                            @keydown.enter.prevent="saveLocalNodeDisplayName"
                        />
                        <button
                            type="button"
                            class="inline-flex size-8 items-center justify-center rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted hover:text-emerald-600"
                            :title="$t('tools.propagation_nodes.save_name')"
                            @click="saveLocalNodeDisplayName"
                        >
                            <MaterialDesignIcon icon-name="check" class="size-4" />
                        </button>
                        <button
                            type="button"
                            class="inline-flex size-8 items-center justify-center rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted"
                            :title="$t('tools.propagation_nodes.reset_name')"
                            @click="resetLocalNodeDisplayName"
                        >
                            <MaterialDesignIcon icon-name="restore" class="size-4" />
                        </button>
                    </div>
                </label>
                <div
                    v-if="localNodeStatsVisible"
                    class="text-[11px] text-sem-fg-muted flex flex-wrap gap-x-3 gap-y-0.5"
                >
                    <span>{{
                        $t("tools.propagation_nodes.stats_uptime", {
                            time: formatSeconds(localPropagationNode.local_node_stats.uptime_seconds),
                        })
                    }}</span>
                    <span>{{
                        $t("tools.propagation_nodes.stats_peers", {
                            count: localPropagationNode.local_node_stats.total_peers,
                        })
                    }}</span>
                    <span>{{
                        $t("tools.propagation_nodes.stats_messages", {
                            count: localPropagationNode.local_node_stats.messagestore_count,
                        })
                    }}</span>
                    <span>{{
                        $t("tools.propagation_nodes.stats_received", {
                            count: localPropagationNode.local_node_stats.client_messages_received,
                        })
                    }}</span>
                    <span>{{
                        $t("tools.propagation_nodes.stats_served", {
                            count: localPropagationNode.local_node_stats.client_messages_served,
                        })
                    }}</span>
                    <span>{{
                        $t("tools.propagation_nodes.stats_storage", {
                            size: formatStorageUsage(localPropagationNode.local_node_stats),
                        })
                    }}</span>
                    <span>RX {{ formatByteSize(localPropagationNode.local_node_stats.rx_bytes) }}</span>
                    <span>TX {{ formatByteSize(localPropagationNode.local_node_stats.tx_bytes) }}</span>
                </div>
                <div v-else class="text-[11px] text-sem-fg-muted">
                    {{ $t("tools.propagation_nodes.stats_when_running") }}
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    <label class="text-[11px] text-sem-fg-muted block">
                        {{ $t("app.incoming_message_size") }}
                        <select
                            v-model="lxmfIncomingDeliveryPreset"
                            class="input-field mt-1 py-1.5 text-sm"
                            @change="onLxmfIncomingDeliveryPresetChange"
                        >
                            <option value="1mb">{{ $t("app.incoming_message_size_1mb") }}</option>
                            <option value="10mb">{{ $t("app.incoming_message_size_10mb") }}</option>
                            <option value="25mb">{{ $t("app.incoming_message_size_25mb") }}</option>
                            <option value="50mb">{{ $t("app.incoming_message_size_50mb") }}</option>
                            <option value="1gb">{{ $t("app.incoming_message_size_1gb") }}</option>
                            <option value="custom">{{ $t("app.incoming_message_size_custom") }}</option>
                        </select>
                        <div
                            v-if="lxmfIncomingDeliveryPreset === 'custom'"
                            class="mt-1 flex flex-wrap items-center gap-2"
                        >
                            <input
                                v-model.number="lxmfIncomingDeliveryCustomAmount"
                                type="number"
                                min="0.001"
                                step="any"
                                class="input-field min-w-0 flex-1 py-1.5 text-sm"
                                @input="onLxmfIncomingDeliveryCustomChange"
                            />
                            <select
                                v-model="lxmfIncomingDeliveryCustomUnit"
                                class="input-field py-1.5 text-sm w-auto"
                                @change="onLxmfIncomingDeliveryCustomChange"
                            >
                                <option value="mb">{{ $t("app.incoming_message_size_unit_mb") }}</option>
                                <option value="gb">{{ $t("app.incoming_message_size_unit_gb") }}</option>
                            </select>
                        </div>
                    </label>
                    <label class="text-[11px] text-sem-fg-muted">
                        {{ $t("tools.propagation_nodes.transfer_limit_mb") }}
                        <input
                            v-model.number="propagationLimitInputMb"
                            type="number"
                            min="0.001"
                            step="0.01"
                            class="input-field mt-1 py-1.5 text-sm"
                            @input="onPropagationTransferLimitChange"
                        />
                    </label>
                    <label class="text-[11px] text-sem-fg-muted">
                        {{ $t("tools.propagation_nodes.sync_limit_mb") }}
                        <input
                            v-model.number="propagationSyncLimitInputMb"
                            type="number"
                            min="0.001"
                            step="0.01"
                            class="input-field mt-1 py-1.5 text-sm"
                            @input="onPropagationSyncLimitChange"
                        />
                    </label>
                </div>
                <label class="block text-[11px] text-sem-fg-muted">
                    {{ $t("tools.propagation_nodes.stamp_cost") }}
                    <input
                        v-model.number="config.lxmf_propagation_node_stamp_cost"
                        type="number"
                        min="13"
                        max="254"
                        class="input-field mt-1 py-1.5 text-sm"
                        @input="onPropagationStampCostChange"
                    />
                </label>
                <button
                    type="button"
                    class="primary-chip text-xs"
                    :disabled="!localPropagationNode"
                    @click="useLocalPropagationNode"
                >
                    {{ $t("tools.propagation_nodes.use_our_node") }}
                </button>
            </div>
        </div>

        <div class="shrink-0 border-b border-sem-border px-3 py-1.5 space-y-1.5">
            <div class="flex items-center gap-2 min-w-0">
                <span class="text-xs font-medium text-sem-fg-muted shrink-0">{{
                    $t("tools.propagation_nodes.preferred_heading")
                }}</span>
                <span
                    v-if="config.lxmf_preferred_propagation_node_destination_hash"
                    class="min-w-0 flex-1 truncate font-mono text-[11px] text-sem-fg-secondary"
                    :title="config.lxmf_preferred_propagation_node_destination_hash"
                >
                    {{ formatDestinationHash(config.lxmf_preferred_propagation_node_destination_hash) }}
                </span>
                <span v-else class="min-w-0 flex-1 truncate text-[11px] text-sem-fg-muted">{{
                    $t("tools.propagation_nodes.preferred_none_short")
                }}</span>
                <div
                    v-if="config.lxmf_preferred_propagation_node_destination_hash"
                    class="flex items-center gap-0.5 shrink-0"
                >
                    <button
                        type="button"
                        class="inline-flex size-7 items-center justify-center rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted hover:text-sem-accent"
                        :title="$t('tools.propagation_nodes.copy_hash')"
                        @click="copyPreferredHash"
                    >
                        <MaterialDesignIcon icon-name="content-copy" class="size-4" />
                    </button>
                    <button
                        type="button"
                        class="inline-flex size-7 items-center justify-center rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted hover:text-sem-accent"
                        :title="$t('tools.propagation_nodes.find_path')"
                        @click="requestPathForNode(config.lxmf_preferred_propagation_node_destination_hash)"
                    >
                        <MaterialDesignIcon icon-name="map-marker-path" class="size-4" />
                    </button>
                    <button
                        type="button"
                        class="inline-flex size-7 items-center justify-center rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted hover:text-red-600"
                        :title="$t('tools.propagation_nodes.clear_preferred')"
                        @click="stopUsingPropagationNode"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-4" />
                    </button>
                </div>
            </div>
            <div
                v-if="nodePathFor(config.lxmf_preferred_propagation_node_destination_hash)"
                class="text-[11px] text-sem-fg-muted"
            >
                {{ formatPathLabel(nodePathFor(config.lxmf_preferred_propagation_node_destination_hash)) }}
            </div>
            <p
                v-if="config.lxmf_preferred_propagation_node_auto_select"
                class="text-[11px] text-amber-700 dark:text-amber-300"
            >
                {{ $t("tools.propagation_nodes.auto_select_on_notice") }}
            </p>
            <div class="flex gap-1.5">
                <input
                    v-model="manualHashDraft"
                    type="text"
                    spellcheck="false"
                    autocomplete="off"
                    :placeholder="$t('tools.propagation_nodes.manual_placeholder')"
                    :title="$t('tools.propagation_nodes.manual_hint')"
                    class="input-field min-w-0 flex-1 py-1.5 font-mono text-xs"
                    @keydown.enter.prevent="setPreferredFromDraft"
                    @paste="onManualHashPaste"
                />
                <button type="button" class="secondary-chip shrink-0 text-xs px-3 py-1.5" @click="pastePreferredHash">
                    {{ $t("tools.propagation_nodes.paste_hash") }}
                </button>
                <button
                    type="button"
                    class="primary-chip shrink-0 text-xs px-3 py-1.5"
                    :disabled="isSavingPreferred || !manualHashDraft"
                    @click="setPreferredFromDraft"
                >
                    {{ $t("tools.propagation_nodes.set_preferred") }}
                </button>
            </div>
        </div>

        <div
            v-if="propagationNodes.length > 0"
            class="shrink-0 flex items-center gap-2 px-3 py-2 border-b border-sem-border"
        >
            <div class="relative min-w-0 flex-1">
                <MaterialDesignIcon
                    icon-name="magnify"
                    class="absolute left-3 top-1/2 -translate-y-1/2 size-5 text-sem-fg-muted pointer-events-none"
                />
                <input
                    v-model="searchTerm"
                    type="search"
                    data-testid="prop-nodes-search"
                    :placeholder="$t('tools.propagation_nodes.search_placeholder', { count: propagationNodes.length })"
                    class="input-field pl-11! py-2 text-sm"
                />
            </div>
            <select
                v-model="sortBy"
                data-testid="prop-nodes-sort"
                class="shrink-0 w-44 bg-sem-surface-muted border border-sem-border text-sm rounded-2xl px-2.5 py-2 text-sem-fg"
            >
                <option value="preferred">{{ $t("tools.propagation_nodes.sort_preferred") }}</option>
                <option value="recent">{{ $t("tools.propagation_nodes.sort_recent") }}</option>
                <option value="oldest">{{ $t("tools.propagation_nodes.sort_oldest") }}</option>
                <option value="name">{{ $t("tools.propagation_nodes.sort_name") }}</option>
                <option value="name-desc">{{ $t("tools.propagation_nodes.sort_name_desc") }}</option>
            </select>
        </div>

        <div data-testid="prop-nodes-list" class="flex-1 min-h-0 overflow-y-auto">
            <div
                v-if="paginatedNodes.length > 0"
                class="divide-y divide-sem-border"
                role="radiogroup"
                :aria-label="$t('tools.propagation_nodes.preferred_heading')"
            >
                <div
                    v-for="propagationNode of paginatedNodes"
                    :key="propagationNode.destination_hash"
                    class="flex items-center gap-0.5 hover:bg-sem-surface-muted/60"
                    :class="{
                        'bg-blue-50/70 dark:bg-blue-950/20': isPreferredNode(propagationNode.destination_hash),
                    }"
                >
                    <button
                        type="button"
                        role="radio"
                        :aria-checked="isPreferredNode(propagationNode.destination_hash) ? 'true' : 'false'"
                        :data-testid="'prop-node-' + propagationNode.destination_hash"
                        class="flex min-w-0 flex-1 items-center gap-2.5 px-3 py-2 text-left"
                        :title="
                            isPreferredNode(propagationNode.destination_hash)
                                ? $t('tools.propagation_nodes.preferred_badge')
                                : $t('tools.propagation_nodes.set_as_preferred')
                        "
                        @click="selectPreferredNode(propagationNode.destination_hash)"
                    >
                        <MaterialDesignIcon
                            :icon-name="
                                isPreferredNode(propagationNode.destination_hash) ? 'radiobox-marked' : 'radiobox-blank'
                            "
                            class="size-5 shrink-0"
                            :class="
                                isPreferredNode(propagationNode.destination_hash)
                                    ? 'text-sem-accent'
                                    : 'text-sem-fg-muted'
                            "
                        />
                        <div class="min-w-0 flex-1">
                            <div class="flex items-center gap-1.5 min-w-0">
                                <span class="truncate text-sm font-medium">{{
                                    propagationNode.operator_display_name ||
                                    $t("tools.propagation_nodes.unknown_operator")
                                }}</span>
                                <span
                                    v-if="propagationNode.is_propagation_enabled === false"
                                    class="shrink-0 rounded-full bg-red-100 dark:bg-red-900/30 px-1.5 text-[10px] font-semibold text-red-700 dark:text-red-300"
                                >
                                    {{ $t("tools.propagation_nodes.disabled") }}
                                </span>
                                <span
                                    v-if="propagationNode.is_local_node"
                                    class="shrink-0 rounded-full bg-emerald-100 dark:bg-emerald-900/30 px-1.5 text-[10px] font-semibold text-emerald-700 dark:text-emerald-300"
                                >
                                    {{ $t("tools.propagation_nodes.our_node") }}
                                </span>
                            </div>
                            <div
                                class="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-sem-fg-muted"
                            >
                                <span class="font-mono truncate" :title="propagationNode.destination_hash">{{
                                    formatDestinationHash(propagationNode.destination_hash)
                                }}</span>
                                <span>{{
                                    $t("tools.propagation_nodes.announced_ago", {
                                        time: formatTimeAgo(propagationNode.updated_at),
                                    })
                                }}</span>
                                <span>{{ formatPathLabel(nodePathFor(propagationNode.destination_hash)) }}</span>
                            </div>
                        </div>
                    </button>
                    <button
                        type="button"
                        class="inline-flex size-8 shrink-0 items-center justify-center rounded-lg mr-2 text-sem-fg-muted hover:bg-sem-surface-muted hover:text-sem-accent"
                        :title="$t('tools.propagation_nodes.find_path')"
                        @click="requestPathForNode(propagationNode.destination_hash)"
                    >
                        <MaterialDesignIcon icon-name="map-marker-path" class="size-4" />
                    </button>
                </div>
            </div>

            <div
                v-if="totalPages > 1"
                class="flex items-center justify-between gap-2 px-3 py-2 border-t border-sem-border text-xs text-sem-fg-muted"
            >
                <span>{{
                    $t("tools.propagation_nodes.showing_range", {
                        start: startIndex + 1,
                        end: endIndex,
                        total: sortedAndSearchedPropagationNodes.length,
                    })
                }}</span>
                <div class="flex items-center gap-1">
                    <button
                        :disabled="currentPage === 1"
                        type="button"
                        class="secondary-chip text-xs px-2 py-1 disabled:opacity-40"
                        @click="currentPage = Math.max(1, currentPage - 1)"
                    >
                        {{ $t("tools.propagation_nodes.previous") }}
                    </button>
                    <button
                        :disabled="currentPage === totalPages"
                        type="button"
                        class="secondary-chip text-xs px-2 py-1 disabled:opacity-40"
                        @click="currentPage = Math.min(totalPages, currentPage + 1)"
                    >
                        {{ $t("tools.propagation_nodes.next") }}
                    </button>
                </div>
            </div>

            <div
                v-if="sortedAndSearchedPropagationNodes.length === 0"
                class="flex h-full min-h-40 items-center justify-center px-4 text-center"
            >
                <div v-if="propagationNodes.length === 0" class="flex flex-col items-center text-sem-fg-muted">
                    <MaterialDesignIcon icon-name="mailbox" class="size-8 mb-2 opacity-70" />
                    <div class="font-semibold text-sem-fg">{{ $t("tools.propagation_nodes.no_nodes_title") }}</div>
                    <div class="text-sm mt-1">{{ $t("tools.propagation_nodes.empty_announced") }}</div>
                    <button type="button" class="primary-chip mt-3 text-xs" @click="loadPropagationNodes">
                        {{ $t("tools.propagation_nodes.reload") }}
                    </button>
                </div>
                <div v-else-if="searchTerm !== ''" class="flex flex-col items-center text-sem-fg-muted">
                    <MaterialDesignIcon icon-name="magnify" class="size-8 mb-2 opacity-70" />
                    <div class="font-semibold text-sem-fg">{{ $t("tools.propagation_nodes.no_search_title") }}</div>
                    <div class="text-sm mt-1">{{ $t("tools.propagation_nodes.no_search_hint") }}</div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import Utils from "../../js/Utils";
import WebSocketConnection from "../../js/WebSocketConnection";
import ToastUtils from "../../js/ToastUtils";
import { copyTextToClipboard, readTextFromClipboard } from "../../js/clipboardUtils.js";
import { getDestinationPath } from "../../js/reticulumPathfinding.js";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToolsPageHeader from "../tools/ToolsPageHeader.vue";
import {
    incomingDeliveryBytesFromCustom,
    incomingDeliveryBytesFromPresetKey,
    syncIncomingDeliveryFieldsFromBytes,
} from "../../js/settings/incomingDeliveryLimit";

export default {
    name: "PropagationNodesPage",
    components: {
        MaterialDesignIcon,
        ToolsPageHeader,
    },
    data() {
        return {
            searchTerm: "",
            sortBy: "preferred",
            propagationNodes: [],
            config: {
                lxmf_preferred_propagation_node_destination_hash: null,
                lxmf_preferred_propagation_node_auto_select: false,
                lxmf_local_propagation_node_address_hash: null,
                lxmf_delivery_transfer_limit_in_bytes: 1000 * 1000 * 10,
                lxmf_propagation_transfer_limit_in_bytes: 1000 * 256,
                lxmf_propagation_sync_limit_in_bytes: 1000 * 10240,
                lxmf_propagation_node_stamp_cost: 16,
            },
            manualHashDraft: "",
            isSavingPreferred: false,
            currentPage: 1,
            itemsPerPage: 20,
            saveTimeouts: {
                deliveryLimit: null,
                propagationLimit: null,
                propagationSyncLimit: null,
                propagationStampCost: null,
            },
            isLocalManagerCollapsed: true,
            localNodeDisplayNameDraft: "",
            lxmfIncomingDeliveryPreset: "10mb",
            lxmfIncomingDeliveryCustomAmount: 10,
            lxmfIncomingDeliveryCustomUnit: "mb",
            propagationLimitInputMb: 0,
            propagationSyncLimitInputMb: 0,
            nodePathsByHash: {},
        };
    },
    computed: {
        localPropagationNode() {
            return this.propagationNodes.find((node) => node.is_local_node) ?? null;
        },
        localNodeIsRunning() {
            const running = this.localPropagationNode?.local_node_stats?.is_running;
            if (typeof running === "boolean") {
                return running;
            }
            return Boolean(this.localPropagationNode?.is_propagation_enabled);
        },
        localNodeStatsVisible() {
            return Boolean(this.localPropagationNode?.local_node_stats && this.localNodeIsRunning);
        },
        searchedPropagationNodes() {
            return this.propagationNodes.filter((propagationNode) => {
                const search = this.searchTerm.toLowerCase();
                const matchesOperatorDisplayName =
                    propagationNode.operator_display_name?.toLowerCase()?.includes(search) ?? false;
                const matchesDestinationHash = propagationNode.destination_hash.toLowerCase().includes(search);
                return matchesOperatorDisplayName || matchesDestinationHash;
            });
        },
        sortedAndSearchedPropagationNodes() {
            let nodes = [...this.searchedPropagationNodes];

            switch (this.sortBy) {
                case "name":
                    nodes.sort((a, b) => {
                        const nameA = (
                            a.operator_display_name || this.$t("tools.propagation_nodes.unknown_operator")
                        ).toLowerCase();
                        const nameB = (
                            b.operator_display_name || this.$t("tools.propagation_nodes.unknown_operator")
                        ).toLowerCase();
                        return nameA.localeCompare(nameB);
                    });
                    break;
                case "name-desc":
                    nodes.sort((a, b) => {
                        const nameA = (
                            a.operator_display_name || this.$t("tools.propagation_nodes.unknown_operator")
                        ).toLowerCase();
                        const nameB = (
                            b.operator_display_name || this.$t("tools.propagation_nodes.unknown_operator")
                        ).toLowerCase();
                        return nameB.localeCompare(nameA);
                    });
                    break;
                case "recent":
                    nodes.sort((a, b) => {
                        const timeA = new Date(a.updated_at).getTime();
                        const timeB = new Date(b.updated_at).getTime();
                        return timeB - timeA;
                    });
                    break;
                case "oldest":
                    nodes.sort((a, b) => {
                        const timeA = new Date(a.updated_at).getTime();
                        const timeB = new Date(b.updated_at).getTime();
                        return timeA - timeB;
                    });
                    break;
                case "preferred":
                default:
                    nodes.sort((a, b) => {
                        const aIsPreferred =
                            this.config.lxmf_preferred_propagation_node_destination_hash === a.destination_hash;
                        const bIsPreferred =
                            this.config.lxmf_preferred_propagation_node_destination_hash === b.destination_hash;
                        if (aIsPreferred && !bIsPreferred) return -1;
                        if (!aIsPreferred && bIsPreferred) return 1;
                        if (a.is_local_node && !b.is_local_node) return -1;
                        if (!a.is_local_node && b.is_local_node) return 1;
                        const timeA = new Date(a.updated_at).getTime();
                        const timeB = new Date(b.updated_at).getTime();
                        return timeB - timeA;
                    });
                    break;
            }

            return nodes;
        },
        totalPages() {
            return Math.ceil(this.sortedAndSearchedPropagationNodes.length / this.itemsPerPage);
        },
        startIndex() {
            return (this.currentPage - 1) * this.itemsPerPage;
        },
        endIndex() {
            return Math.min(this.startIndex + this.itemsPerPage, this.sortedAndSearchedPropagationNodes.length);
        },
        paginatedNodes() {
            return this.sortedAndSearchedPropagationNodes.slice(this.startIndex, this.endIndex);
        },
    },
    watch: {
        searchTerm() {
            this.currentPage = 1;
        },
        sortBy() {
            this.currentPage = 1;
        },
    },
    beforeUnmount() {
        // stop listening for websocket messages
        WebSocketConnection.off("message", this.onWebsocketMessage);
        for (const timeoutKey of Object.keys(this.saveTimeouts)) {
            if (this.saveTimeouts[timeoutKey]) {
                clearTimeout(this.saveTimeouts[timeoutKey]);
            }
        }
    },
    mounted() {
        // listen for websocket messages
        WebSocketConnection.on("message", this.onWebsocketMessage);

        if (window.matchMedia && window.matchMedia("(max-width: 640px)").matches) {
            this.isLocalManagerCollapsed = true;
        }
        this.getConfig();
        this.loadPropagationNodes();
    },
    methods: {
        async onWebsocketMessage(message) {
            let json = null;
            try {
                json = JSON.parse(message.data);
            } catch (e) {
                console.error(e);
                return;
            }
            switch (json.type) {
                case "config": {
                    this.config = json.config;
                    this.syncManagerInputsFromConfig();
                    this.syncManualHashDraftFromConfig();
                    break;
                }
            }
        },
        async getConfig() {
            try {
                const response = await window.api.get("/api/v1/config");
                this.config = response.data.config;
                this.syncManagerInputsFromConfig();
                this.syncManualHashDraftFromConfig();
            } catch (e) {
                console.log(e);
                ToastUtils.error(this.$t("common.save_failed"));
            }
        },
        async updateConfig(config) {
            try {
                const response = await window.api.patch("/api/v1/config", config);
                this.config = response.data.config;
                this.syncManagerInputsFromConfig();
                return true;
            } catch (e) {
                ToastUtils.error(this.$t("common.save_failed"));
                console.log(e);
                return false;
            }
        },
        async loadPropagationNodes() {
            try {
                const response = await window.api.get(`/api/v1/lxmf/propagation-nodes`, {
                    params: {
                        limit: 500,
                    },
                });
                this.propagationNodes = response.data.lxmf_propagation_nodes;
                await this.refreshPriorityNodePaths();
            } catch {
                ToastUtils.error(this.$t("tools.propagation_nodes.load_failed"));
            }
        },
        async usePropagationNode(destination_hash) {
            const parsed = Utils.parseDestinationHash(destination_hash);
            if (!parsed) {
                ToastUtils.error(this.$t("tools.propagation_nodes.invalid_hash"));
                return false;
            }
            const patch = {
                lxmf_preferred_propagation_node_destination_hash: parsed,
            };
            if (this.config.lxmf_preferred_propagation_node_auto_select) {
                patch.lxmf_preferred_propagation_node_auto_select = false;
            }
            const didUpdate = await this.updateConfig(patch);
            if (!didUpdate) {
                return false;
            }
            this.manualHashDraft = parsed;
            ToastUtils.success(this.$t("tools.propagation_nodes.preferred_set"));
            await this.requestPathForNode(parsed);
            return true;
        },
        isPreferredNode(destinationHash) {
            return this.config.lxmf_preferred_propagation_node_destination_hash === destinationHash;
        },
        async selectPreferredNode(destinationHash) {
            if (this.isPreferredNode(destinationHash)) {
                return;
            }
            await this.usePropagationNode(destinationHash);
        },
        async stopUsingPropagationNode() {
            const didUpdate = await this.updateConfig({
                lxmf_preferred_propagation_node_destination_hash: null,
            });
            if (!didUpdate) {
                return;
            }
            this.manualHashDraft = "";
            ToastUtils.success(this.$t("tools.propagation_nodes.preferred_cleared"));
        },
        syncManualHashDraftFromConfig() {
            const preferred = this.config.lxmf_preferred_propagation_node_destination_hash || "";
            this.manualHashDraft = preferred;
        },
        onManualHashPaste(event) {
            const text = event.clipboardData?.getData("text") || "";
            const parsed = Utils.parseDestinationHash(text);
            if (!parsed) {
                return;
            }
            event.preventDefault();
            this.manualHashDraft = parsed;
        },
        async pastePreferredHash() {
            const result = await readTextFromClipboard();
            if (!result.ok) {
                ToastUtils.error(this.$t("messages.failed_read_clipboard"));
                return;
            }
            const parsed = Utils.parseDestinationHash(result.text);
            if (!parsed) {
                ToastUtils.error(this.$t("tools.propagation_nodes.invalid_hash"));
                return;
            }
            this.manualHashDraft = parsed;
            await this.usePropagationNode(parsed);
        },
        async copyPreferredHash() {
            const hash = this.config.lxmf_preferred_propagation_node_destination_hash;
            if (!hash) {
                return;
            }
            const ok = await copyTextToClipboard(hash);
            if (ok) {
                ToastUtils.success(this.$t("common.copied"));
            } else {
                ToastUtils.error(this.$t("common.failed_to_copy"));
            }
        },
        async setPreferredFromDraft() {
            if (this.isSavingPreferred) {
                return;
            }
            this.isSavingPreferred = true;
            try {
                await this.usePropagationNode(this.manualHashDraft);
            } finally {
                this.isSavingPreferred = false;
            }
        },
        async useLocalPropagationNode() {
            if (!this.localPropagationNode) return;
            await this.usePropagationNode(this.localPropagationNode.destination_hash);
            await this.requestPathForNode(this.localPropagationNode.destination_hash);
        },
        async restartLocalPropagationNode() {
            try {
                await window.api.post("/api/v1/lxmf/propagation-node/restart");
                ToastUtils.success(this.$t("tools.propagation_nodes.local_restarted"));
                await Promise.all([this.getConfig(), this.loadPropagationNodes()]);
                await this.refreshPriorityNodePaths();
            } catch {
                ToastUtils.error(this.$t("common.save_failed"));
            }
        },
        async stopLocalPropagationNode() {
            try {
                await window.api.post("/api/v1/lxmf/propagation-node/stop");
                ToastUtils.success(this.$t("tools.propagation_nodes.local_stopped"));
                await Promise.all([this.getConfig(), this.loadPropagationNodes()]);
                await this.refreshPriorityNodePaths();
            } catch {
                ToastUtils.error(this.$t("common.save_failed"));
            }
        },
        async startLocalPropagationNode() {
            try {
                const didUpdate = await this.updateConfig({ lxmf_local_propagation_node_enabled: true });
                if (!didUpdate) {
                    return;
                }
                ToastUtils.success(this.$t("tools.propagation_nodes.local_started"));
                await Promise.all([this.getConfig(), this.loadPropagationNodes()]);
                await this.refreshPriorityNodePaths();
            } catch {
                ToastUtils.error(this.$t("common.save_failed"));
            }
        },
        async announceNow(showSuccessToast = true) {
            try {
                await window.api.get("/api/v1/announce");
                if (showSuccessToast) {
                    ToastUtils.success(this.$t("tools.propagation_nodes.announce_triggered"));
                }
                await this.loadPropagationNodes();
                await this.refreshPriorityNodePaths();
            } catch {
                ToastUtils.error(this.$t("common.save_failed"));
            }
        },
        async saveLocalNodeDisplayName() {
            const nextName = (this.localNodeDisplayNameDraft || "").trim() || "Anonymous Peer";
            try {
                const didUpdate = await this.updateConfig({ display_name: nextName });
                if (!didUpdate) {
                    return;
                }
                this.localNodeDisplayNameDraft = nextName;
                await this.announceNow(false);
                ToastUtils.success(this.$t("tools.propagation_nodes.name_saved"));
                await this.loadPropagationNodes();
                await this.refreshPriorityNodePaths();
            } catch {
                ToastUtils.error(this.$t("common.save_failed"));
            }
        },
        async resetLocalNodeDisplayName() {
            this.localNodeDisplayNameDraft = "Anonymous Peer";
            await this.saveLocalNodeDisplayName();
        },
        syncManagerInputsFromConfig() {
            const displayName = (this.config.display_name || "").trim();
            this.localNodeDisplayNameDraft = displayName || "Anonymous Peer";
            const incoming = syncIncomingDeliveryFieldsFromBytes(this.config.lxmf_delivery_transfer_limit_in_bytes);
            this.lxmfIncomingDeliveryPreset = incoming.preset;
            this.lxmfIncomingDeliveryCustomAmount = incoming.customAmount;
            this.lxmfIncomingDeliveryCustomUnit = incoming.customUnit;
            this.propagationLimitInputMb = this.bytesToMb(this.config.lxmf_propagation_transfer_limit_in_bytes);
            this.propagationSyncLimitInputMb = this.bytesToMb(this.config.lxmf_propagation_sync_limit_in_bytes);
        },
        bytesToMb(value) {
            const n = Number(value);
            if (!Number.isFinite(n) || n <= 0) {
                return 0;
            }
            return Math.max(0.001, Math.round((n / 1000000) * 1000) / 1000);
        },
        mbToBytes(value) {
            const n = Number(value);
            if (!Number.isFinite(n) || n <= 0) {
                return 1000;
            }
            return Math.max(1000, Math.round(n * 1000000));
        },
        async refreshPriorityNodePaths() {
            const hashes = new Set();
            const localHash = this.config.lxmf_local_propagation_node_address_hash;
            if (localHash) {
                hashes.add(localHash);
            }
            const preferredHash = this.config.lxmf_preferred_propagation_node_destination_hash;
            if (preferredHash) {
                hashes.add(preferredHash);
            }
            for (const hash of hashes) {
                await this.requestPathForNode(hash);
            }
        },
        async requestPathForNode(destinationHash) {
            const hash = (destinationHash || "").trim();
            if (!hash) {
                return;
            }
            try {
                const response = await getDestinationPath(window.api, hash, {
                    request: "1",
                    timeout: 4,
                });
                this.nodePathsByHash = {
                    ...this.nodePathsByHash,
                    [hash]: response.data.path || null,
                };
            } catch {
                this.nodePathsByHash = {
                    ...this.nodePathsByHash,
                    [hash]: null,
                };
            }
        },
        nodePathFor(destinationHash) {
            const hash = (destinationHash || "").trim();
            if (!hash) {
                return null;
            }
            return this.nodePathsByHash[hash] || null;
        },
        formatPathLabel(path) {
            if (!path) {
                return this.$t("tools.propagation_nodes.no_path");
            }
            const hops = Number(path.hops);
            let hopsText = this.$t("tools.propagation_nodes.unknown_hops");
            if (Number.isFinite(hops)) {
                hopsText =
                    hops === 1
                        ? this.$t("tools.propagation_nodes.hop_one")
                        : this.$t("tools.propagation_nodes.hop_many", { count: hops });
            }
            const iface = path.next_hop_interface || this.$t("tools.propagation_nodes.unknown_interface");
            return this.$t("tools.propagation_nodes.path_via", { hops: hopsText, iface });
        },
        formatDestinationHash(hash) {
            return Utils.formatDestinationHash(hash);
        },
        async onLxmfIncomingDeliveryPresetChange() {
            if (this.lxmfIncomingDeliveryPreset === "custom") {
                const incoming = syncIncomingDeliveryFieldsFromBytes(this.config.lxmf_delivery_transfer_limit_in_bytes);
                this.lxmfIncomingDeliveryCustomAmount = incoming.customAmount;
                this.lxmfIncomingDeliveryCustomUnit = incoming.customUnit;
                return;
            }
            const bytes = incomingDeliveryBytesFromPresetKey(this.lxmfIncomingDeliveryPreset);
            if (bytes == null) {
                return;
            }
            await this.updateConfig({
                lxmf_delivery_transfer_limit_in_bytes: bytes,
            });
        },
        onLxmfIncomingDeliveryCustomChange() {
            if (this.lxmfIncomingDeliveryPreset !== "custom") {
                return;
            }
            if (this.saveTimeouts.deliveryLimit) clearTimeout(this.saveTimeouts.deliveryLimit);
            this.saveTimeouts.deliveryLimit = setTimeout(async () => {
                await this.updateConfig({
                    lxmf_delivery_transfer_limit_in_bytes: incomingDeliveryBytesFromCustom(
                        this.lxmfIncomingDeliveryCustomAmount,
                        this.lxmfIncomingDeliveryCustomUnit
                    ),
                });
            }, 450);
        },
        onPropagationTransferLimitChange() {
            if (this.saveTimeouts.propagationLimit) clearTimeout(this.saveTimeouts.propagationLimit);
            this.saveTimeouts.propagationLimit = setTimeout(async () => {
                await this.updateConfig({
                    lxmf_propagation_transfer_limit_in_bytes: this.mbToBytes(this.propagationLimitInputMb),
                });
            }, 450);
        },
        onPropagationSyncLimitChange() {
            if (this.saveTimeouts.propagationSyncLimit) clearTimeout(this.saveTimeouts.propagationSyncLimit);
            this.saveTimeouts.propagationSyncLimit = setTimeout(async () => {
                await this.updateConfig({
                    lxmf_propagation_sync_limit_in_bytes: this.mbToBytes(this.propagationSyncLimitInputMb),
                });
            }, 450);
        },
        onPropagationStampCostChange() {
            if (this.saveTimeouts.propagationStampCost) clearTimeout(this.saveTimeouts.propagationStampCost);
            this.saveTimeouts.propagationStampCost = setTimeout(async () => {
                let cost = Number(this.config.lxmf_propagation_node_stamp_cost);
                if (!Number.isFinite(cost) || cost < 13) {
                    cost = 13;
                } else if (cost > 254) {
                    cost = 254;
                }
                this.config.lxmf_propagation_node_stamp_cost = cost;
                await this.updateConfig({
                    lxmf_propagation_node_stamp_cost: cost,
                });
            }, 450);
        },
        formatTimeAgo: function (datetimeString) {
            return Utils.formatTimeAgo(datetimeString);
        },
        formatSeconds(seconds) {
            if (seconds == null || Number.isNaN(Number(seconds))) return "0s";
            const total = Math.max(0, Number(seconds));
            if (total < 60) return `${Math.floor(total)}s`;
            const minutes = Math.floor(total / 60);
            if (minutes < 60) return `${minutes}m`;
            const hours = Math.floor(minutes / 60);
            if (hours < 24) return `${hours}h`;
            const days = Math.floor(hours / 24);
            return `${days}d`;
        },
        formatByteSize(bytes) {
            const value = Number(bytes);
            if (!Number.isFinite(value) || value < 0) return "0 B";
            if (value < 1000) return `${Math.round(value)} B`;
            if (value < 1000 * 1000) return `${(value / 1000).toFixed(1)} KB`;
            if (value < 1000 * 1000 * 1000) return `${(value / (1000 * 1000)).toFixed(2)} MB`;
            return `${(value / (1000 * 1000 * 1000)).toFixed(2)} GB`;
        },
        formatStorageUsage(stats) {
            if (!stats || typeof stats !== "object") {
                return "0 B";
            }
            const used = this.formatByteSize(stats.messagestore_bytes);
            const limitValue = Number(stats.messagestore_limit_bytes);
            if (!Number.isFinite(limitValue) || limitValue <= 0) {
                return used;
            }
            return `${used} / ${this.formatByteSize(limitValue)}`;
        },
    },
};
</script>
