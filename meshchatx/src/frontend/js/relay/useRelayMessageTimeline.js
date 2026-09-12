// @ts-check

import { computed, nextTick, ref, watch } from "vue";

import * as rrcApi from "../api/rrc.js";
import {
    buildRelayMessageTimeline,
    filterUniqueOlderRelayMessages,
    relayMessageKey,
    relayMessageTimelineSignature,
    RELAY_MESSAGES_PREVIOUS_PAGE_SIZE,
} from "../relayMessageTimeline.js";

const LOAD_PREVIOUS_SCROLL_EDGE_PX = 200;

/**
 * Message timeline state for RelayChatPage: the raw messages list, the
 * cached display timeline (date dividers and presence groups), previous-page
 * pagination, and presence-group expansion.
 *
 * The host keeps room selection and DOM glue. options.getSelectedHubHash and
 * options.getSelectedRoom report the open room so stale page loads can bail,
 * options.getMessagesScrollElement returns the scroll container used to keep
 * position stable after prepending older messages, options.encodeRoom
 * URL-encodes room names for API paths, options.prependTimelineCache delegates
 * to the host's _prependMessageTimelineCache (underscore-prefixed methods are
 * not proxied from setup state), and options.t translates presence group
 * summary labels.
 */
export function useRelayMessageTimeline(options = {}) {
    const { getSelectedHubHash, getSelectedRoom, getMessagesScrollElement, encodeRoom, prependTimelineCache, t } =
        options;

    const messages = ref([]);
    const messageTimelineCache = ref(null);
    const messageTimelineCacheSignature = ref("");
    const hasMorePrevious = ref(false);
    const isLoadingPrevious = ref(false);
    const loadPreviousInFlight = ref(0);
    const roomSelectSequence = ref(0);
    const expandedPresenceGroups = ref({});

    const messageTimeline = computed(() => {
        if (messageTimelineCache.value !== null) {
            return messageTimelineCache.value;
        }
        return buildRelayMessageTimeline(messages.value);
    });

    const oldestLoadedSeq = computed(() => {
        let minSeq = null;
        for (const msg of messages.value) {
            if (typeof msg.seq !== "number") {
                continue;
            }
            if (minSeq === null || msg.seq < minSeq) {
                minSeq = msg.seq;
            }
        }
        return minSeq;
    });

    watch(
        messages,
        (msgs) => {
            const sig = relayMessageTimelineSignature(msgs);
            if (messageTimelineCache.value === null || messageTimelineCacheSignature.value !== sig) {
                messageTimelineCache.value = buildRelayMessageTimeline(msgs);
                messageTimelineCacheSignature.value = sig;
            }
        },
        { deep: true, immediate: true }
    );

    async function loadPreviousMessages() {
        if (isLoadingPrevious.value || !hasMorePrevious.value || !getSelectedHubHash?.() || !getSelectedRoom?.()) {
            return;
        }
        const beforeSeq = oldestLoadedSeq.value;
        if (beforeSeq === null) {
            hasMorePrevious.value = false;
            return;
        }
        const seq = roomSelectSequence.value;
        const hubHash = getSelectedHubHash();
        const room = getSelectedRoom();
        loadPreviousInFlight.value += 1;
        isLoadingPrevious.value = true;
        try {
            const response = await rrcApi.getHubsRoomsMessages(hubHash, encodeRoom(room), {
                params: { limit: RELAY_MESSAGES_PREVIOUS_PAGE_SIZE, before_seq: beforeSeq },
            });
            if (seq !== roomSelectSequence.value || hubHash !== getSelectedHubHash() || room !== getSelectedRoom()) {
                return;
            }
            const older = response.data?.messages || [];
            hasMorePrevious.value = Boolean(response.data?.has_more);
            if (older.length === 0) {
                return;
            }
            const uniqueOlder = filterUniqueOlderRelayMessages(older, messages.value);
            if (uniqueOlder.length === 0) {
                if (older.length > 0) {
                    hasMorePrevious.value = false;
                }
                return;
            }
            const scrollEl = getMessagesScrollElement?.() ?? null;
            const prevScrollHeight = scrollEl ? scrollEl.scrollHeight : 0;
            const prevScrollTop = scrollEl ? scrollEl.scrollTop : 0;
            messages.value = [...uniqueOlder, ...messages.value];
            prependTimelineCache?.(uniqueOlder);
            if (scrollEl) {
                nextTick(() => {
                    const delta = scrollEl.scrollHeight - prevScrollHeight;
                    scrollEl.scrollTop = prevScrollTop + delta;
                });
            }
        } catch {
            hasMorePrevious.value = false;
        } finally {
            loadPreviousInFlight.value = Math.max(0, loadPreviousInFlight.value - 1);
            isLoadingPrevious.value = loadPreviousInFlight.value > 0;
        }
    }

    function onMessagesScroll(event) {
        const el = event.target;
        if (!el || isLoadingPrevious.value || !hasMorePrevious.value) {
            return;
        }
        if (el.scrollTop <= LOAD_PREVIOUS_SCROLL_EDGE_PX) {
            void loadPreviousMessages();
        }
    }

    function timelineEntryKey(entry, index = 0) {
        if (entry.type === "dateDivider") {
            return `date-${entry.dayKey}-${index}`;
        }
        if (entry.type === "presenceGroup") {
            return `presence-${entry.id}-${index}`;
        }
        const msgKey = relayMessageKey(entry.msg);
        return msgKey ? `${msgKey}-${index}` : `idx-${index}`;
    }

    function isPresenceGroupExpanded(groupId) {
        return !!expandedPresenceGroups.value[groupId];
    }

    function togglePresenceGroup(groupId) {
        if (!groupId) {
            return;
        }
        expandedPresenceGroups.value[groupId] = !expandedPresenceGroups.value[groupId];
    }

    function formatPresenceGroupSummary(entry) {
        const joined = Number(entry?.joinedCount) || 0;
        const left = Number(entry?.leftCount) || 0;
        const connection = Number(entry?.connectionCount) || 0;
        const parts = [];
        if (joined > 0) {
            parts.push(t?.("relay_chat.presence_joined", { count: joined }));
        }
        if (left > 0) {
            parts.push(t?.("relay_chat.presence_left", { count: left }));
        }
        if (connection > 0) {
            parts.push(t?.("relay_chat.presence_connection", { count: connection }));
        }
        if (parts.length === 0) {
            return t?.("relay_chat.presence_events", {
                count: Array.isArray(entry?.messages) ? entry.messages.length : 0,
            });
        }
        return parts.join(" · ");
    }

    return {
        messages,
        messageTimelineCache,
        messageTimelineCacheSignature,
        hasMorePrevious,
        isLoadingPrevious,
        loadPreviousInFlight,
        roomSelectSequence,
        expandedPresenceGroups,
        messageTimeline,
        oldestLoadedSeq,
        loadPreviousMessages,
        onMessagesScroll,
        timelineEntryKey,
        isPresenceGroupExpanded,
        togglePresenceGroup,
        formatPresenceGroupSummary,
    };
}
