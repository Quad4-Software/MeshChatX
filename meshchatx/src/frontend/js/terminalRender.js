// SPDX-License-Identifier: 0BSD

const ESC = "\u001b";

const OSC_SEQUENCE = new RegExp(`${ESC}\\][^\\u0007${ESC}]*(?:\\u0007|${ESC}\\\\)`, "g");
const STRING_SEQUENCE = new RegExp(`${ESC}[P^_][^${ESC}]*${ESC}\\\\`, "g");
const CSI_SEQUENCE = new RegExp(`${ESC}\\[[0-?]*[ -/]*[@-~]`, "g");
const SINGLE_ESCAPE = new RegExp(`${ESC}[@-Z\\\\-_]`, "g");
// eslint-disable-next-line no-control-regex
const STRIP_CONTROL = /[\u0000-\u0007\u000b\u000c\u000e-\u001f\u007f]/g;
const TAB_WIDTH = 8;

/**
 * Strip ANSI escape and control sequences, preserving newline, carriage
 * return, tab and backspace which are handled by the cursor simulation.
 *
 * @param {string} input
 * @returns {string}
 */
function stripAnsi(input) {
    return input
        .replace(OSC_SEQUENCE, "")
        .replace(STRING_SEQUENCE, "")
        .replace(CSI_SEQUENCE, "")
        .replace(SINGLE_ESCAPE, "")
        .replace(STRIP_CONTROL, "");
}

/**
 * Convert raw pseudo-terminal output into readable plain text.
 *
 * ANSI colour and cursor-control sequences are removed, while carriage
 * returns, backspaces and tabs are applied so that progress redraws and
 * line edits collapse into their final visible form.
 *
 * @param {string} raw
 * @returns {string}
 */
export function renderTerminalOutput(raw) {
    if (typeof raw !== "string" || raw.length === 0) {
        return "";
    }

    const cleaned = stripAnsi(raw);
    const rows = [[]];
    let row = 0;
    let col = 0;

    for (const ch of cleaned) {
        if (ch === "\n") {
            row += 1;
            if (!rows[row]) {
                rows[row] = [];
            }
            col = 0;
        } else if (ch === "\r") {
            col = 0;
        } else if (ch === "\b") {
            col = Math.max(0, col - 1);
        } else if (ch === "\t") {
            const stop = col + (TAB_WIDTH - (col % TAB_WIDTH));
            while (col < stop) {
                if (rows[row][col] === undefined) {
                    rows[row][col] = " ";
                }
                col += 1;
            }
        } else {
            rows[row][col] = ch;
            col += 1;
        }
    }

    return rows
        .map((cells) => {
            let line = "";
            for (let i = 0; i < cells.length; i += 1) {
                line += cells[i] === undefined ? " " : cells[i];
            }
            return line.replace(/\s+$/, "");
        })
        .join("\n");
}

export default renderTerminalOutput;
