import Utils from "./Utils";
import LinkUtils from "./LinkUtils";

export default class MarkdownRenderer {
    /**
     * A simple Markdown to HTML renderer, cause we dont need another library for this.
     * Ported and simplified from meshchatx/src/backend/markdown_renderer.py
     */
    static render(text) {
        if (text == null) {
            return "";
        }
        if (typeof text !== "string") {
            text = String(text);
        }

        text = Utils.escapeHtml(text);

        // Fenced code blocks - process these FIRST and replace with placeholders
        const code_blocks = [];
        // eslint-disable-next-line security/detect-unsafe-regex -- bounded fenced block, lazy match
        text = text.replace(/```(\w+)?\n([\s\S]*?)\n```/g, (match, lang, code) => {
            const placeholder = `[[CB${code_blocks.length}]]`;
            code_blocks.push(
                `<pre class="bg-gray-800 dark:bg-zinc-900 text-zinc-100 dark:text-zinc-100 p-3 rounded-lg my-3 overflow-x-auto border border-gray-700 dark:border-zinc-800 font-mono text-sm"><code class="language-${lang || ""} text-inherit">${code}</code></pre>`
            );
            return placeholder;
        });

        // Inline code before emphasis so snake_case inside `code` / ``code`` is safe.
        const inline_codes = [];
        const pushInline = (code) => {
            const placeholder = `[[IC${inline_codes.length}]]`;
            inline_codes.push(
                `<code class="bg-black/10 dark:bg-white/10 px-1 rounded-sm font-mono text-[0.9em]">${code}</code>`
            );
            return placeholder;
        };
        text = text.replace(/``([^`]+)``/g, (_m, code) => pushInline(code));
        text = text.replace(/`([^`]+)`/g, (_m, code) => pushInline(code));

        // Headers
        text = text.replace(/^# (.*)$/gm, '<h1 class="text-xl font-bold mt-4 mb-2"> $1</h1>');
        text = text.replace(/^## (.*)$/gm, '<h2 class="text-lg font-bold mt-3 mb-1">$1</h2>');
        text = text.replace(/^### (.*)$/gm, '<h3 class="text-base font-bold mt-2 mb-1">$1</h3>');

        // Bold and Italic
        text = text.replace(/\*\*\*(.*?)\*\*\*/g, "<strong><em>$1</em></strong>");
        text = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        text = text.replace(/\*(.*?)\*/g, "<em>$1</em>");
        text = text.replace(/(^|[^\w])___(.*?)___(?=[^\w]|$)/g, "$1<strong><em>$2</em></strong>");
        text = text.replace(/(^|[^\w])__(.*?)__(?=[^\w]|$)/g, "$1<strong>$2</strong>");
        text = text.replace(/(^|[^\w])_(.*?)_(?=[^\w]|$)/g, "$1<em>$2</em>");

        // Blockquotes
        text = text.replace(
            /^> (.*)$/gm,
            '<blockquote class="border-l-4 border-gray-300 dark:border-zinc-700 pl-3 py-1 my-2 italic opacity-80">$1</blockquote>'
        );

        // Links
        text = LinkUtils.renderAllLinks(text);

        // Restore inline code then fenced blocks (single pass; avoid O(n*m) replace loops)
        text = text.replace(/\[\[IC(\d+)\]\]/g, (_m, idx) => inline_codes[Number(idx)] ?? _m);
        text = text.replace(/\[\[CB(\d+)\]\]/g, (_m, idx) => code_blocks[Number(idx)] ?? _m);

        // Paragraphs - double newline to p tag
        const parts = text.split(/\n\n+/);
        const processed_parts = [];
        for (let part of parts) {
            part = part.trim();
            if (!part) continue;

            // If it's a placeholder for code block, don't wrap in <p>
            if (part.startsWith("<pre") || part.startsWith("<h")) {
                processed_parts.push(part);
            } else {
                // Replace single newlines with <br> for line breaks within paragraphs
                part = part.replace(/\n/g, "<br>");
                processed_parts.push(`<p class="my-2 leading-relaxed">${part}</p>`);
            }
        }

        return processed_parts.join("\n");
    }

    /**
     * True when the body is only a single emoji (after markdown strip), for large bubble rendering.
     */
    static isSingleEmojiMessage(raw) {
        if (raw == null || typeof raw !== "string") {
            return false;
        }
        let plain = MarkdownRenderer.strip(raw);
        plain = plain.replace(/\s+/g, "");
        if (!plain) {
            return false;
        }
        if (typeof Intl === "undefined" || typeof Intl.Segmenter !== "function") {
            return false;
        }
        const seg = new Intl.Segmenter(undefined, { granularity: "grapheme" });
        const clusters = [...seg.segment(plain)].map((s) => s.segment);
        if (clusters.length !== 1) {
            return false;
        }
        const g = clusters[0];
        return /\p{Extended_Pictographic}/u.test(g) || /\p{Emoji}/u.test(g);
    }

    /**
     * Strips markdown from text for previews.
     */
    static strip(text) {
        if (text == null) {
            return "";
        }
        if (typeof text !== "string") {
            text = String(text);
        }

        // Strip fenced code blocks
        // eslint-disable-next-line security/detect-unsafe-regex -- bounded fenced block, lazy match
        text = text.replace(/```(\w+)?\n([\s\S]*?)\n```/g, "[Code Block]");

        // Strip inline code (double then single)
        text = text.replace(/``([^`]+)``/g, "$1");
        text = text.replace(/`([^`]+)`/g, "$1");

        // Strip headers
        text = text.replace(/^#+ (.*)$/gm, "$1");

        // Strip bold and italic
        text = text.replace(/\*\*\*(.*?)\*\*\*/g, "$1");
        text = text.replace(/\*\*(.*?)\*\*/g, "$1");
        text = text.replace(/\*(.*?)\*/g, "$1");
        text = text.replace(/(^|[^\w])___(.*?)___(?=[^\w]|$)/g, "$1$2");
        text = text.replace(/(^|[^\w])__(.*?)__(?=[^\w]|$)/g, "$1$2");
        text = text.replace(/(^|[^\w])_(.*?)_(?=[^\w]|$)/g, "$1$2");

        return text;
    }
}
