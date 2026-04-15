export function getViewCanvasBounds(network) {
    const container = document.getElementById("network");
    if (!container || !network) return null;
    const scale = network.getScale();
    const vp = network.getViewPosition();
    const w = container.clientWidth;
    const h = container.clientHeight;
    const halfW = w / (2 * scale);
    const halfH = h / (2 * scale);
    return {
        left: vp.x - halfW,
        right: vp.x + halfW,
        top: vp.y - halfH,
        bottom: vp.y + halfH,
        scale,
    };
}
