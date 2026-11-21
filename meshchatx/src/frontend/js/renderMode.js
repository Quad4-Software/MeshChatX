// SPDX-License-Identifier: 0BSD
// Render-mode flag for the desktop shell. The Wails bridge reports
// renderMode "software" inside Flatpak and when GPU compositing is off,
// where WebKitGTK repaints whole layers during opacity transitions and
// route changes visibly flicker. With the flag on <html>, style.css
// disables the route fade there.

export function resolveRenderMode(runtimeInfo) {
    return runtimeInfo && runtimeInfo.renderMode === "software" ? "software" : "hardware";
}

export function applyRenderMode(root, runtimeInfo) {
    const mode = resolveRenderMode(runtimeInfo);
    if (root && root.dataset) {
        root.dataset.renderMode = mode;
    }
    return mode;
}
