export function getPositionAlongTrail(trail, distBehind) {
    if (!trail || trail.length === 0) return { x: 0, y: 0 };
    if (trail.length === 1) return { ...trail[0] };
    let d = 0;
    for (let i = trail.length - 1; i > 0; i--) {
        const p = trail[i];
        const q = trail[i - 1];
        const seg = Math.hypot(p.x - q.x, p.y - q.y);
        if (d + seg >= distBehind) {
            const t = seg > 0 ? (distBehind - d) / seg : 0;
            return { x: p.x + (q.x - p.x) * t, y: p.y + (q.y - p.y) * t };
        }
        d += seg;
    }
    return { ...trail[0] };
}
