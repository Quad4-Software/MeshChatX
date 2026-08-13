// SPDX-License-Identifier: 0BSD

import { NAV_EDIT_HOLD_MS, NAV_EDIT_HOLD_MOVE_PX } from "./appSidebarNavLayout.js";

export const navEditHoldMixin = {
    data() {
        return {
            navHoldTimer: null,
            navHoldArmed: false,
            navHoldX: 0,
            navHoldY: 0,
            draggingKind: "",
            draggingId: "",
            dragOverKey: "",
        };
    },
    beforeUnmount() {
        this.clearNavHold();
    },
    methods: {
        canStartNavHold() {
            return !this.isCollapsed && !this.isEditing;
        },
        clearNavHold() {
            if (this.navHoldTimer != null) {
                clearTimeout(this.navHoldTimer);
                this.navHoldTimer = null;
            }
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
            try {
                event.currentTarget.setPointerCapture?.(event.pointerId);
            } catch {
                // pointer capture is optional
            }
            this.navHoldTimer = setTimeout(() => {
                this.navHoldTimer = null;
                this.navHoldArmed = true;
                this.$emit("edit-start");
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
