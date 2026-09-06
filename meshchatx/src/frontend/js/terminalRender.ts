// SPDX-License-Identifier: 0BSD

const ESC = "\u001b";

const OSC_SEQUENCE = new RegExp(`${ESC}\\][^\\u0007${ESC}]*(?:\\u0007|${ESC}\\\\)`, "g");
const STRING_SEQUENCE = new RegExp(`${ESC}[P^_][^${ESC}]*${ESC}\\\\`, "g");
const CSI_SEQUENCE = new RegExp(`${ESC}\\[[0-?]*[ -/]*[@-~]`, "g");
const SINGLE_ESCAPE = new RegExp(`${ESC}[@-Z\\\\-_]`, "g");

const TAB_WIDTH = 8;

/** Drop C0 controls except NL, CR, HT, BS (handled by cursor simulation). */
function stripOtherControls(input: string): string {
    let out = "";
    for (const ch of input) {
        const c = ch.charCodeAt(0);
        if (c === 9 || c === 10 || c === 13 || c === 8) {
            out += ch;
            continue;
        }
        if (c <= 31 || c === 127) {
            continue;
        }
        out += ch;
    }
    return out;
}

/**
 * Strip ANSI escape and control sequences, preserving newline, carriage
 * return, tab and backspace which are handled by the cursor simulation.
 */
function stripAnsi(input: string): string {
    return stripOtherControls(
        input
            .replace(OSC_SEQUENCE, "")
            .replace(STRING_SEQUENCE, "")
            .replace(CSI_SEQUENCE, "")
            .replace(SINGLE_ESCAPE, "")
    );
}

/**
 * Convert raw pseudo-terminal output into readable plain text.
 *
 * ANSI colour and cursor-control sequences are removed, while carriage
 * returns, backspaces and tabs are applied so that progress redraws and
 * line edits collapse into their final visible form.
 */
export function renderTerminalOutput(raw: string): string {
    if (typeof raw !== "string" || raw.length === 0) {
        return "";
    }

    const cleaned = stripAnsi(raw);
    const rows: string[][] = [[]];
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
