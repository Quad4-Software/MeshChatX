// SPDX-License-Identifier: 0BSD

import { NAV_EDIT_HOLD_MS, NAV_EDIT_HOLD_MOVE_PX } from "../../../js/appSidebarNavLayout.js";

export const NAV_EDIT_CLICK_GUARD_MS = 400;

export interface NavDragState {
    draggingKind: string;
    draggingId: string;
    dragOverKey: string;
}

export class NavEditHoldController {
    private navHoldTimer: ReturnType<typeof setTimeout> | null = null;
    private navHoldClickGuardTimer: ReturnType<typeof setTimeout> | null = null;
    private navHoldArmed = false;
    private navHoldX = 0;
    private navHoldY = 0;
    private navHoldReleaseBound = false;

    public draggingKind = "";
    public draggingId = "";
    public dragOverKey = "";

    constructor(
        private isCollapsed: () => boolean,
        private isEditing: () => boolean,
        private onEditStart: () => void,
        private onStateChange?: () => void
    ) {}

    private notify() {
        this.onStateChange?.();
    }

    private canStartNavHold(): boolean {
        return !this.isCollapsed() && !this.isEditing();
    }

    private bindNavHoldReleaseListeners() {
        if (this.navHoldReleaseBound || typeof window === "undefined") {
            return;
        }
        this.navHoldReleaseBound = true;
        window.addEventListener("pointerup", this.onWindowRelease, true);
        window.addEventListener("pointercancel", this.onWindowRelease, true);
    }

    private unbindNavHoldReleaseListeners() {
        if (!this.navHoldReleaseBound || typeof window === "undefined") {
            this.navHoldReleaseBound = false;
            return;
        }
        this.navHoldReleaseBound = false;
        window.removeEventListener("pointerup", this.onWindowRelease, true);
        window.removeEventListener("pointercancel", this.onWindowRelease, true);
    }

    private onWindowRelease = () => {
        this.onPointerUp();
    };

    private clearNavHoldTimer() {
        if (this.navHoldTimer != null) {
            clearTimeout(this.navHoldTimer);
            this.navHoldTimer = null;
        }
    }

    private clearNavHoldClickGuard() {
        if (this.navHoldClickGuardTimer != null) {
            clearTimeout(this.navHoldClickGuardTimer);
            this.navHoldClickGuardTimer = null;
        }
    }

    public clearNavHold() {
        this.clearNavHoldTimer();
        this.unbindNavHoldReleaseListeners();
    }

    public reset() {
        this.clearNavHold();
        this.clearNavHoldClickGuard();
        this.navHoldArmed = false;
        this.clearNavDrag();
    }

    public onPointerDown(event: PointerEvent) {
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
            this.onEditStart();
            this.clearNavHoldClickGuard();
            this.navHoldClickGuardTimer = setTimeout(() => {
                this.navHoldClickGuardTimer = null;
                this.navHoldArmed = false;
            }, NAV_EDIT_CLICK_GUARD_MS);
        }, NAV_EDIT_HOLD_MS);
    }

    public onPointerMove(event: PointerEvent) {
        if (this.navHoldTimer == null) {
            return;
        }
        const dx = event.clientX - this.navHoldX;
        const dy = event.clientY - this.navHoldY;
        if (dx * dx + dy * dy > NAV_EDIT_HOLD_MOVE_PX * NAV_EDIT_HOLD_MOVE_PX) {
            this.clearNavHold();
        }
    }

    public onPointerUp() {
        this.clearNavHold();
    }

    public onClickCapture(event: MouseEvent) {
        if (!this.navHoldArmed) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        this.navHoldArmed = false;
        this.clearNavHoldClickGuard();
    }

    public onContextMenu(event: MouseEvent) {
        if (this.navHoldTimer != null || this.navHoldArmed || this.isEditing()) {
            event.preventDefault();
        }
    }

    public clearNavDrag() {
        if (!this.draggingKind && !this.draggingId && !this.dragOverKey) {
            return;
        }
        this.draggingKind = "";
        this.draggingId = "";
        this.dragOverKey = "";
        this.notify();
    }

    public beginNavDrag(kind: string, id: string, event: DragEvent): boolean {
        if (!this.isEditing()) {
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
            /* some browsers block drag metadata */
        }
        this.notify();
        return true;
    }

    public setNavDragOver(key: string, event: DragEvent) {
        if (!this.isEditing() || !this.draggingKind) {
            return;
        }
        this.dragOverKey = key;
        if (event.dataTransfer) {
            event.dataTransfer.dropEffect = "move";
        }
        this.notify();
    }

    public dropPosition(event: DragEvent): "before" | "after" {
        const target = event.currentTarget as HTMLElement | null;
        if (!target) return "after";
        const rect = target.getBoundingClientRect();
        return event.clientY > rect.top + rect.height / 2 ? "after" : "before";
    }
}
