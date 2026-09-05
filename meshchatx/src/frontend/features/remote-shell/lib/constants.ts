// SPDX-License-Identifier: 0BSD

import type { RemoteShellLayoutState } from "./types.js";

export const MAX_OUTPUT_BUFFER_LENGTH = 250000;
export const NARROW_BREAKPOINT_PX = 1024;

export const EMPTY_LAYOUT: RemoteShellLayoutState = {
    selectedSessionId: null,
};
