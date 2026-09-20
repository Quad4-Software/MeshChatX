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
// Bounds the in-memory window during deep scroll-back. Dropped tail entries
// are refetched when the user scrolls back to the newest edge.
const MAX_RELAY_MESSAGES = 2000;

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
 * not proxied from setup state), options.reloadLatest re-anchors the window on
 * the newest page after the tail was trimmed, options.excludeMessage hides
 * locally ignored messages from older-page loads, options.decorateMessages
 * applies client-side flags (like custom highlight words) to older pages,
 * options.onScrollState reports distance-to-bottom on every scroll for the
 * new-messages pill, and options.t translates presence group summary labels.
 */
export function useRelayMessageTimeline(options = {}) {
    const {
        getSelectedHubHash,
        getSelectedRoom,
        getMessagesScrollElement,
        encodeRoom,
        prependTimelineCache,
        reloadLatest,
        excludeMessage,
        decorateMessages,
        buildTimelineOptions,
        onScrollState,
        t,
    } = options;

    const getTimelineOptions = () =>
        typeof buildTimelineOptions === "function" ? buildTimelineOptions() : {};

    const messages = ref([]);
    const messageTimelineCache = ref(null);
    const messageTimelineCacheSignature = ref("");
    const hasMorePrevious = ref(false);
    const isLoadingPrevious = ref(false);
    const loadPreviousInFlight = ref(0);
    const roomSelectSequence = ref(0);
    const expandedPresenceGroups = ref({});
    const tailTrimmed = ref(false);
    const reloadingLatest = ref(false);
    let headTrimQueued = false;

    const messageTimeline = computed(() => {
        if (messageTimelineCache.value !== null) {
            return messageTimelineCache.value;
        }
        return buildRelayMessageTimeline(messages.value, getTimelineOptions());
    });

    const messageKeySet = computed(() => {
        const set = new Set();
        for (const msg of messages.value) {
            const key = relayMessageKey(msg);
            if (key) {
                set.add(key);
            }
        }
        return set;
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
            if (msgs.length === 0) {
                tailTrimmed.value = false;
            }
            const sig = relayMessageTimelineSignature(msgs);
            if (messageTimelineCache.value === null || messageTimelineCacheSignature.value !== sig) {
                messageTimelineCache.value = buildRelayMessageTimeline(msgs, getTimelineOptions());
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
            // Locally ignored peers never enter the display list, but the
            // pagination window still tracks their seq numbers so history
            // walks do not stall on a filtered page.
            const visibleOlder = excludeMessage ? uniqueOlder.filter((m) => !excludeMessage(m)) : uniqueOlder;
            decorateMessages?.(visibleOlder);
            const scrollEl = getMessagesScrollElement?.() ?? null;
            const prevScrollHeight = scrollEl ? scrollEl.scrollHeight : 0;
            const prevScrollTop = scrollEl ? scrollEl.scrollTop : 0;
            messages.value = [...visibleOlder, ...messages.value];
            prependTimelineCache?.(visibleOlder);
            // Trim after the anchor is restored: removed tail entries sit below
            // the viewport, so scrollTop stays valid.
            const trimTail = () => {
                if (messages.value.length > MAX_RELAY_MESSAGES) {
                    messages.value.splice(MAX_RELAY_MESSAGES);
                    tailTrimmed.value = true;
                }
            };
            if (scrollEl) {
                nextTick(() => {
                    const delta = scrollEl.scrollHeight - prevScrollHeight;
                    scrollEl.scrollTop = prevScrollTop + delta;
                    trimTail();
                });
            } else {
                nextTick(trimTail);
            }
        } catch {
            // Keep hasMorePrevious: one transient failure must not permanently
            // disable history loading for the open room.
        } finally {
            loadPreviousInFlight.value = Math.max(0, loadPreviousInFlight.value - 1);
            isLoadingPrevious.value = loadPreviousInFlight.value > 0;
        }
    }

    // Live append path. Dedupes via the computed key set (O(1) per message
    // instead of a full rescan) and drops the oldest entries past the cap,
    // re-anchoring the scroll position for readers in history.
    function pushLiveMessage(msg) {
        const key = relayMessageKey(msg);
        if (key && messageKeySet.value.has(key)) {
            return false;
        }
        messages.value.push(msg);
        if (messages.value.length <= MAX_RELAY_MESSAGES || headTrimQueued) {
            return true;
        }
        headTrimQueued = true;
        const scrollEl = getMessagesScrollElement?.() ?? null;
        const trimNow = () => {
            headTrimQueued = false;
            // Compute the drop live: pushes landing in the same tick must not
            // each schedule a splice against a stale length, or a burst
            // removes far more than the overflow.
            const drop = messages.value.length - MAX_RELAY_MESSAGES;
            if (drop <= 0) {
                return;
            }
            if (!scrollEl) {
                messages.value.splice(0, drop);
                return;
            }
            const prevScrollHeight = scrollEl.scrollHeight;
            const prevScrollTop = scrollEl.scrollTop;
            messages.value.splice(0, drop);
            nextTick(() => {
                scrollEl.scrollTop = Math.max(0, prevScrollTop - (prevScrollHeight - scrollEl.scrollHeight));
            });
        };
        if (!scrollEl) {
            trimNow();
            return true;
        }
        nextTick(trimNow);
        return true;
    }

    function onMessagesScroll(event) {
        const el = event.target;
        if (!el) {
            return;
        }
        const distanceToBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
        onScrollState?.(el, distanceToBottom);
        if (tailTrimmed.value && distanceToBottom <= LOAD_PREVIOUS_SCROLL_EDGE_PX && !reloadingLatest.value) {
            reloadingLatest.value = true;
            tailTrimmed.value = false;
            Promise.resolve(reloadLatest?.()).finally(() => {
                reloadingLatest.value = false;
            });
            return;
        }
        if (isLoadingPrevious.value || !hasMorePrevious.value) {
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
        tailTrimmed,
        reloadingLatest,
        messageTimeline,
        oldestLoadedSeq,
        loadPreviousMessages,
        pushLiveMessage,
        onMessagesScroll,
        timelineEntryKey,
        isPresenceGroupExpanded,
        togglePresenceGroup,
        formatPresenceGroupSummary,
    };
}
