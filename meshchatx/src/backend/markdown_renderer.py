import re
import html


class MarkdownRenderer:
    """A simple Markdown to HTML renderer."""

    @staticmethod
    def render(text):
        if not text:
            return ""

        # Escape HTML entities first to prevent XSS
        # Use a more limited escape if we want to allow some things,
        # but for docs, full escape is safest.
        text = html.escape(text)

        # Fenced code blocks - process these FIRST and replace with placeholders
        # to avoid other regexes mangling the code content
        code_blocks = []

        def code_block_placeholder(match):
            lang = match.group(1) or ""
            code = match.group(2)
            placeholder = f"[[CB{len(code_blocks)}]]"
            code_blocks.append(
                f'<pre class="bg-gray-800 dark:bg-zinc-900 text-gray-100 p-4 rounded-lg my-4 overflow-x-auto border border-gray-700 dark:border-zinc-800 font-mono text-sm"><code class="language-{lang}">{code}</code></pre>'
            )
            return placeholder

        text = re.sub(
            r"```(\w+)?\n(.*?)\n```", code_block_placeholder, text, flags=re.DOTALL
        )

        # Horizontal Rules
        text = re.sub(
            r"^---+$",
            r'<hr class="my-8 border-t border-gray-200 dark:border-zinc-800">',
            text,
            flags=re.MULTILINE,
        )

        # Headers
        text = re.sub(
            r"^# (.*)$",
            r'<h1 class="text-3xl font-bold mt-8 mb-4 text-gray-900 dark:text-zinc-100">\1</h1>',
            text,
            flags=re.MULTILINE,
        )
        text = re.sub(
            r"^## (.*)$",
            r'<h2 class="text-2xl font-bold mt-6 mb-3 text-gray-900 dark:text-zinc-100">\1</h2>',
            text,
            flags=re.MULTILINE,
        )
        text = re.sub(
            r"^### (.*)$",
            r'<h3 class="text-xl font-bold mt-4 mb-2 text-gray-900 dark:text-zinc-100">\1</h3>',
            text,
            flags=re.MULTILINE,
        )
        text = re.sub(
            r"^#### (.*)$",
            r'<h4 class="text-lg font-bold mt-3 mb-2 text-gray-900 dark:text-zinc-100">\1</h4>',
            text,
            flags=re.MULTILINE,
        )

        # Bold and Italic
        text = re.sub(r"\*\*\*(.*?)\*\*\*", r"<strong><em>\1</em></strong>", text)
        text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"\*(.*?)\*", r"<em>\1</em>", text)
        text = re.sub(r"___(.*?)___", r"<strong><em>\1</em></strong>", text)
        text = re.sub(r"__(.*?)__", r"<strong>\1</strong>", text)
        text = re.sub(r"_(.*?)_", r"<em>\1</em>", text)

        # Strikethrough
        text = re.sub(r"~~(.*?)~~", r"<del>\1</del>", text)

        # Inline code
        text = re.sub(
            r"`([^`]+)`",
            r'<code class="bg-gray-100 dark:bg-zinc-800 px-1.5 py-0.5 rounded text-pink-600 dark:text-pink-400 font-mono text-[0.9em]">\1</code>',
            text,
        )

        # Task lists
        text = re.sub(
            r"^[-*] \[ \] (.*)$",
            r'<li class="flex items-start gap-2 list-none"><input type="checkbox" disabled class="mt-1"> <span>\1</span></li>',
            text,
            flags=re.MULTILINE,
        )
        text = re.sub(
            r"^[-*] \[x\] (.*)$",
            r'<li class="flex items-start gap-2 list-none"><input type="checkbox" checked disabled class="mt-1"> <span class="line-through opacity-50">\1</span></li>',
            text,
            flags=re.MULTILINE,
        )

        # Links
        text = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)",
            r'<a href="\2" class="text-blue-600 dark:text-blue-400 hover:underline" target="_blank">\1</a>',
            text,
        )

        # Images
        text = re.sub(
            r"!\[([^\]]*)\]\(([^)]+)\)",
            r'<div class="my-6"><img src="\2" alt="\1" class="max-w-full h-auto rounded-xl shadow-lg border border-gray-100 dark:border-zinc-800"></div>',
            text,
        )

        # Blockquotes
        text = re.sub(
            r"^> (.*)$",
            r'<blockquote class="border-l-4 border-blue-500/50 pl-4 py-2 my-6 italic bg-gray-50 dark:bg-zinc-900/50 text-gray-700 dark:text-zinc-300 rounded-r-lg">\1</blockquote>',
            text,
            flags=re.MULTILINE,
        )

        # Lists - Simple single level for now to keep it predictable
        def unordered_list_repl(match):
            items = match.group(0).strip().split("\n")
            html_items = ""
            for i in items:
                # Check if it's already a task list item
                if 'type="checkbox"' in i:
                    html_items += i
                else:
                    content = i[2:].strip()
                    html_items += f'<li class="ml-4 mb-1 list-disc text-gray-700 dark:text-zinc-300">{content}</li>'
            return f'<ul class="my-4 space-y-1">{html_items}</ul>'

        text = re.sub(
            r"((?:^[*-] .*\n?)+)", unordered_list_repl, text, flags=re.MULTILINE
        )

        def ordered_list_repl(match):
            items = match.group(0).strip().split("\n")
            html_items = ""
            for i in items:
                content = re.sub(r"^\d+\. ", "", i).strip()
                html_items += f'<li class="ml-4 mb-1 list-decimal text-gray-700 dark:text-zinc-300">{content}</li>'
            return f'<ol class="my-4 space-y-1">{html_items}</ol>'

        text = re.sub(
            r"((?:^\d+\. .*\n?)+)", ordered_list_repl, text, flags=re.MULTILINE
        )

        # Paragraphs - double newline to p tag
        parts = text.split("\n\n")
        processed_parts = []
        for part in parts:
            part = part.strip()
            if not part:
                continue

            # If it's a placeholder for code block, don't wrap in <p>
            if part.startswith("[[CB") and part.endswith("]]"):
                processed_parts.append(part)
                continue

            # If it already starts with a block tag, don't wrap in <p>
            if re.match(r"^<(h\d|ul|ol|li|blockquote|hr|div)", part):
                processed_parts.append(part)
            else:
                # Replace single newlines with <br> for line breaks within paragraphs
                part = part.replace("\n", "<br>")
                processed_parts.append(
                    f'<p class="my-4 leading-relaxed text-gray-800 dark:text-zinc-200">{part}</p>'
                )

        text = "\n".join(processed_parts)

        # Restore code blocks
        for i, code_html in enumerate(code_blocks):
            text = text.replace(f"[[CB{i}]]", code_html)

        return text
