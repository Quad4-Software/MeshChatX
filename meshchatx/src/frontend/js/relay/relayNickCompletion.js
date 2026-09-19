// SPDX-License-Identifier: 0BSD

/**
 * IRC-style Tab nick completion for the relay composer.
 *
 * nickCompletionStep is a pure state machine: given the composer text, caret
 * position, the room's member names, and the previous cycle state it returns
 * the next text/caret/cycle triple, or null when nothing matches. At the
 * start of the input the completion renders as "@nick: " (reply convention);
 * mid-line it renders as "@nick " matching insertMention. Repeated Tab cycles
 * forward through matches, Shift+Tab cycles backwards.
 */

export function squashRelayNick(name) {
    return String(name || "").replace(/\s/g, "");
}

function completionToken(text, caret) {
    let start = caret;
    while (start > 0 && !/\s/.test(text[start - 1])) {
        start -= 1;
    }
    return {
        start,
        end: caret,
        token: text.slice(start, caret),
        atLineStart: start === 0,
    };
}

function insertionFor(state) {
    return state.atLineStart ? `@${state.matches[state.idx]}: ` : `@${state.matches[state.idx]} `;
}

export function relayNickCompletionStep({ text, caret, names, cycle = null, backwards = false }) {
    if (typeof text !== "string" || !Array.isArray(names) || names.length === 0) {
        return null;
    }
    caret = Math.max(0, Math.min(Number(caret) || 0, text.length));

    let state;
    if (cycle && caret === cycle.end && text.slice(cycle.start, cycle.end) === cycle.inserted) {
        const dir = backwards ? -1 : 1;
        state = {
            ...cycle,
            idx: (cycle.idx + dir + cycle.matches.length) % cycle.matches.length,
        };
    } else {
        const t = completionToken(text, caret);
        const raw = t.token.startsWith("@") ? t.token.slice(1) : t.token;
        const lower = raw.toLowerCase();
        const uniq = new Map();
        for (const name of names) {
            const squashed = squashRelayNick(name);
            if (!squashed) {
                continue;
            }
            const key = squashed.toLowerCase();
            if (uniq.has(key) || (lower && !key.startsWith(lower))) {
                continue;
            }
            uniq.set(key, squashed);
        }
        const matches = [...uniq.values()].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
        if (matches.length === 0) {
            return null;
        }
        state = { start: t.start, end: t.end, matches, idx: 0, atLineStart: t.atLineStart };
    }

    const insertion = insertionFor(state);
    const newText = text.slice(0, state.start) + insertion + text.slice(state.end);
    const newEnd = state.start + insertion.length;
    return {
        text: newText,
        caret: newEnd,
        cycle: { ...state, end: newEnd, inserted: insertion },
    };
}
