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

        // Headers
        text = text.replace(/^# (.*)$/gm, '<h1 class="text-xl font-bold mt-4 mb-2"> $1</h1>');
        text = text.replace(/^## (.*)$/gm, '<h2 class="text-lg font-bold mt-3 mb-1">$1</h2>');
        text = text.replace(/^### (.*)$/gm, '<h3 class="text-base font-bold mt-2 mb-1">$1</h3>');

        // Bold and Italic
        text = text.replace(/\*\*\*(.*?)\*\*\*/g, "<strong><em>$1</em></strong>");
        text = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        text = text.replace(/\*(.*?)\*/g, "<em>$1</em>");
        text = text.replace(/___(.*?)___/g, "<strong><em>$1</em></strong>");
        text = text.replace(/__(.*?)__/g, "<strong>$1</strong>");
        text = text.replace(/_(.*?)_/g, "<em>$1</em>");

        // Blockquotes
        text = text.replace(
            /^> (.*)$/gm,
            '<blockquote class="border-l-4 border-gray-300 dark:border-zinc-700 pl-3 py-1 my-2 italic opacity-80">$1</blockquote>'
        );

        // Inline code
        text = text.replace(
            /`([^`]+)`/g,
            '<code class="bg-black/10 dark:bg-white/10 px-1 rounded font-mono text-[0.9em]">$1</code>'
        );

        // Links
        text = LinkUtils.renderAllLinks(text);

        // Restore code blocks
        for (let i = 0; i < code_blocks.length; i++) {
            text = text.replace(`[[CB${i}]]`, code_blocks[i]);
        }

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

        // Strip headers
        text = text.replace(/^#+ (.*)$/gm, "$1");

        // Strip bold and italic
        text = text.replace(/\*\*\*(.*?)\*\*\*/g, "$1");
        text = text.replace(/\*\*(.*?)\*\*/g, "$1");
        text = text.replace(/\*(.*?)\*/g, "$1");
        text = text.replace(/___(.*?)___/g, "$1");
        text = text.replace(/__(.*?)__/g, "$1");
        text = text.replace(/_(.*?)_/g, "$1");

        // Strip inline code
        text = text.replace(/`([^`]+)`/g, "$1");

        return text;
    }
}
