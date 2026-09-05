// SPDX-License-Identifier: 0BSD

import { NAV_EDIT_HOLD_MS, NAV_EDIT_HOLD_MOVE_PX } from "./appSidebarNavLayout.js";

export const NAV_EDIT_CLICK_GUARD_MS = 400;

export const navEditHoldMixin: any = {
    data() {
        return {
            navHoldTimer: null,
            navHoldClickGuardTimer: null,
            navHoldArmed: false,
            navHoldX: 0,
            navHoldY: 0,
            navHoldReleaseBound: false,
            draggingKind: "",
            draggingId: "",
            dragOverKey: "",
        };
    },
    watch: {
        isEditing(editing) {
            if (!editing) {
                this.resetNavEditInteraction();
            }
        },
        isCollapsed(collapsed) {
            if (collapsed) {
                this.resetNavEditInteraction();
            }
        },
    },
    beforeUnmount() {
        this.resetNavEditInteraction();
    },
    methods: {
        canStartNavHold() {
            return !this.isCollapsed && !this.isEditing;
        },
        bindNavHoldReleaseListeners() {
            if (this.navHoldReleaseBound || typeof window === "undefined") {
                return;
            }
            this.navHoldReleaseBound = true;
            window.addEventListener("pointerup", this.onNavHoldWindowRelease, true);
            window.addEventListener("pointercancel", this.onNavHoldWindowRelease, true);
        },
        unbindNavHoldReleaseListeners() {
            if (!this.navHoldReleaseBound || typeof window === "undefined") {
                this.navHoldReleaseBound = false;
                return;
            }
            this.navHoldReleaseBound = false;
            window.removeEventListener("pointerup", this.onNavHoldWindowRelease, true);
            window.removeEventListener("pointercancel", this.onNavHoldWindowRelease, true);
        },
        onNavHoldWindowRelease() {
            this.onNavHoldPointerUp();
        },
        clearNavHoldTimer() {
            if (this.navHoldTimer != null) {
                clearTimeout(this.navHoldTimer);
                this.navHoldTimer = null;
            }
        },
        clearNavHoldClickGuard() {
            if (this.navHoldClickGuardTimer != null) {
                clearTimeout(this.navHoldClickGuardTimer);
                this.navHoldClickGuardTimer = null;
            }
        },
        clearNavHold() {
            this.clearNavHoldTimer();
            this.unbindNavHoldReleaseListeners();
        },
        resetNavEditInteraction() {
            this.clearNavHold();
            this.clearNavHoldClickGuard();
            this.navHoldArmed = false;
            this.clearNavDrag();
        },
        onNavHoldPointerDown(event) {
            if (!this.canStartNavHold()) {
                return;
            }
            if (event.pointerType === "mouse" && event.button !== 0) {
                return;
            }
            this.clearNavHold();
            this.navHoldArmed = false;
            this.navHoldX = event.clientX;
            this.navHoldY = event.clientY;
            this.bindNavHoldReleaseListeners();
            this.navHoldTimer = setTimeout(() => {
                this.navHoldTimer = null;
                this.navHoldArmed = true;
                this.$emit("edit-start");
                this.clearNavHoldClickGuard();
                this.navHoldClickGuardTimer = setTimeout(() => {
                    this.navHoldClickGuardTimer = null;
                    this.navHoldArmed = false;
                }, NAV_EDIT_CLICK_GUARD_MS);
            }, NAV_EDIT_HOLD_MS);
        },
        onNavHoldPointerMove(event) {
            if (this.navHoldTimer == null) {
                return;
            }
            const dx = event.clientX - this.navHoldX;
            const dy = event.clientY - this.navHoldY;
            if (dx * dx + dy * dy > NAV_EDIT_HOLD_MOVE_PX * NAV_EDIT_HOLD_MOVE_PX) {
                this.clearNavHold();
            }
        },
        onNavHoldPointerUp() {
            this.clearNavHold();
        },
        onNavHoldClickCapture(event) {
            if (!this.navHoldArmed) {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            this.navHoldArmed = false;
            this.clearNavHoldClickGuard();
        },
        onNavHoldContextMenu(event) {
            if (this.navHoldTimer != null || this.navHoldArmed || this.isEditing) {
                event.preventDefault();
            }
        },
        clearNavDrag() {
            this.draggingKind = "";
            this.draggingId = "";
            this.dragOverKey = "";
        },
        beginNavDrag(kind, id, event) {
            if (!this.isEditing) {
                event.preventDefault();
                return false;
            }
            this.draggingKind = kind;
            this.draggingId = id;
            try {
                if (event.dataTransfer) {
                    event.dataTransfer.effectAllowed = "move";
                    event.dataTransfer.setData("text/plain", id);
                }
            } catch {
                // some browsers block drag metadata
            }
            return true;
        },
        setNavDragOver(key, event) {
            if (!this.isEditing || !this.draggingKind) {
                return;
            }
            this.dragOverKey = key;
            if (event?.dataTransfer) {
                event.dataTransfer.dropEffect = "move";
            }
        },
        dropPosition(event) {
            const rect = event.currentTarget.getBoundingClientRect();
            return event.clientY > rect.top + rect.height / 2 ? "after" : "before";
        },
    },
};
