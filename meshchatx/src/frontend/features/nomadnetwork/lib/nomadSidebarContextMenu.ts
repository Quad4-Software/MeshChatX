// SPDX-License-Identifier: 0BSD

import { clampFloatingToViewport } from "../../../js/clampFloatingToViewport.js";

export interface ContextMenuPosition {
    left: number;
    top: number;
}

export function calculateContextMenuCoords(x: number, y: number, width = 180, height = 240): ContextMenuPosition {
    const res = clampFloatingToViewport(x, y, width, height);
    return { left: res.left, top: res.top };
}

export interface FavContextMenuState {
    show: boolean;
    x: number;
    y: number;
    targetHash: string;
    targetSectionId: string;
    justOpened: boolean;
}

export interface SecContextMenuState {
    show: boolean;
    x: number;
    y: number;
    sectionId: string;
}

export function createInitialFavContextMenu(): FavContextMenuState {
    return {
        show: false,
        x: 0,
        y: 0,
        targetHash: "",
        targetSectionId: "",
        justOpened: false,
    };
}

export function createInitialSecContextMenu(): SecContextMenuState {
    return {
        show: false,
        x: 0,
        y: 0,
        sectionId: "",
    };
}
