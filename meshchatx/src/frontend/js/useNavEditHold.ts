// SPDX-License-Identifier: 0BSD

import { onBeforeUnmount, ref, watch, type Ref } from "vue";
import { NAV_EDIT_HOLD_MS, NAV_EDIT_HOLD_MOVE_PX } from "./appSidebarNavLayout.js";
import { NAV_EDIT_CLICK_GUARD_MS } from "./appSidebarNavEditHold.js";

export interface UseNavEditHoldOptions {
    isEditing: Ref<boolean>;
    isCollapsed: Ref<boolean>;
    onEditStart: () => void;
}

/**
 * Composition API port of navEditHoldMixin. Hold-to-edit press detection plus
 * drag-reorder bookkeeping for sidebar nav components.
 */
export function useNavEditHold(options: UseNavEditHoldOptions) {
    const navHoldArmed = ref(false);
    const draggingKind = ref("");
    const draggingId = ref("");
    const dragOverKey = ref("");

    let navHoldTimer: ReturnType<typeof setTimeout> | null = null;
    let navHoldClickGuardTimer: ReturnType<typeof setTimeout> | null = null;
    let navHoldX = 0;
    let navHoldY = 0;
    let navHoldReleaseBound = false;

    function canStartNavHold() {
        return !options.isCollapsed.value && !options.isEditing.value;
    }

    function onNavHoldWindowRelease() {
        onNavHoldPointerUp();
    }

    function bindNavHoldReleaseListeners() {
        if (navHoldReleaseBound || typeof window === "undefined") {
            return;
        }
        navHoldReleaseBound = true;
        window.addEventListener("pointerup", onNavHoldWindowRelease, true);
        window.addEventListener("pointercancel", onNavHoldWindowRelease, true);
    }

    function unbindNavHoldReleaseListeners() {
        if (!navHoldReleaseBound || typeof window === "undefined") {
            navHoldReleaseBound = false;
            return;
        }
        navHoldReleaseBound = false;
        window.removeEventListener("pointerup", onNavHoldWindowRelease, true);
        window.removeEventListener("pointercancel", onNavHoldWindowRelease, true);
    }

    function clearNavHoldTimer() {
        if (navHoldTimer != null) {
            clearTimeout(navHoldTimer);
            navHoldTimer = null;
        }
    }

    function clearNavHoldClickGuard() {
        if (navHoldClickGuardTimer != null) {
            clearTimeout(navHoldClickGuardTimer);
            navHoldClickGuardTimer = null;
        }
    }

    function clearNavHold() {
        clearNavHoldTimer();
        unbindNavHoldReleaseListeners();
    }

    function clearNavDrag() {
        draggingKind.value = "";
        draggingId.value = "";
        dragOverKey.value = "";
    }

    function resetNavEditInteraction() {
        clearNavHold();
        clearNavHoldClickGuard();
        navHoldArmed.value = false;
        clearNavDrag();
    }

    function onNavHoldPointerDown(event: PointerEvent) {
        if (!canStartNavHold()) {
            return;
        }
        if (event.pointerType === "mouse" && event.button !== 0) {
            return;
        }
        clearNavHold();
        navHoldArmed.value = false;
        navHoldX = event.clientX;
        navHoldY = event.clientY;
        bindNavHoldReleaseListeners();
        navHoldTimer = setTimeout(() => {
            navHoldTimer = null;
            navHoldArmed.value = true;
            options.onEditStart();
            clearNavHoldClickGuard();
            navHoldClickGuardTimer = setTimeout(() => {
                navHoldClickGuardTimer = null;
                navHoldArmed.value = false;
            }, NAV_EDIT_CLICK_GUARD_MS);
        }, NAV_EDIT_HOLD_MS);
    }

    function onNavHoldPointerMove(event: PointerEvent) {
        if (navHoldTimer == null) {
            return;
        }
        const dx = event.clientX - navHoldX;
        const dy = event.clientY - navHoldY;
        if (dx * dx + dy * dy > NAV_EDIT_HOLD_MOVE_PX * NAV_EDIT_HOLD_MOVE_PX) {
            clearNavHold();
        }
    }

    function onNavHoldPointerUp() {
        clearNavHold();
    }

    function onNavHoldClickCapture(event: MouseEvent) {
        if (!navHoldArmed.value) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        navHoldArmed.value = false;
        clearNavHoldClickGuard();
    }

    function onNavHoldContextMenu(event: MouseEvent) {
        if (navHoldTimer != null || navHoldArmed.value || options.isEditing.value) {
            event.preventDefault();
        }
    }

    function beginNavDrag(kind: string, id: string, event: DragEvent) {
        if (!options.isEditing.value) {
            event.preventDefault();
            return false;
        }
        draggingKind.value = kind;
        draggingId.value = id;
        try {
            if (event.dataTransfer) {
                event.dataTransfer.effectAllowed = "move";
                event.dataTransfer.setData("text/plain", id);
            }
        } catch {
            // some browsers block drag metadata
        }
        return true;
    }

    function setNavDragOver(key: string, event: DragEvent) {
        if (!options.isEditing.value || !draggingKind.value) {
            return;
        }
        dragOverKey.value = key;
        if (event?.dataTransfer) {
            event.dataTransfer.dropEffect = "move";
        }
    }

    function dropPosition(event: DragEvent) {
        const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
        return event.clientY > rect.top + rect.height / 2 ? "after" : "before";
    }

    watch(options.isEditing, (editing) => {
        if (!editing) {
            resetNavEditInteraction();
        }
    });

    watch(options.isCollapsed, (collapsed) => {
        if (collapsed) {
            resetNavEditInteraction();
        }
    });

    onBeforeUnmount(() => {
        resetNavEditInteraction();
    });

    return {
        navHoldArmed,
        draggingKind,
        draggingId,
        dragOverKey,
        clearNavDrag,
        resetNavEditInteraction,
        onNavHoldPointerDown,
        onNavHoldPointerMove,
        onNavHoldPointerUp,
        onNavHoldClickCapture,
        onNavHoldContextMenu,
        beginNavDrag,
        setNavDragOver,
        dropPosition,
    };
}
