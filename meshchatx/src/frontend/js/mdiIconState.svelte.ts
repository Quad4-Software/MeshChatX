// SPDX-License-Identifier: 0BSD

// Bumped when the lazily loaded full @mdi/js library becomes available.
// Components derive icon paths against this so icons that fell back to the
// used-subset placeholder re-resolve once the full path data arrives.
export const mdiIconState = $state({ fullReady: false });
