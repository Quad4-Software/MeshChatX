# SPDX-License-Identifier: 0BSD

import html
import re

_SAFE_LINK_PREFIXES = ("https://", "http://", "/", "#", "mailto:")
_UNSAFE_PROTOCOLS = ("javascript:", "data:", "vbscript:", "file:")


def _safe_href(url):
    if not url or not isinstance(url, str):
        return "#"
    trimmed = url.strip()
    u = trimmed.lower()
    if any(u.startswith(p) for p in _UNSAFE_PROTOCOLS):
        return "#"
    if u.startswith("//"):
        return "#"
    if trimmed.startswith("\\\\"):
        return "#"
    if any(u.startswith(p) for p in _SAFE_LINK_PREFIXES):
        return url
    if ":" in u.split("/")[0]:
        return "#"
    return url


class MarkdownRenderer:
    """A simple Markdown to HTML renderer."""

    _heading_ids: dict[str, int] = {}

    @classmethod
    def _reset_heading_ids(cls):
        cls._heading_ids = {}

    @classmethod
    def _heading_id(cls, text, level):
        slug_base = re.sub(r"[^\w\s-]", "", html.unescape(text)).strip().lower()
        slug_base = re.sub(r"[-\s]+", "-", slug_base) or "section"
        key = f"{level}:{slug_base}"
        count = cls._heading_ids.get(key, 0)
        cls._heading_ids[key] = count + 1
        if count:
            return f"{slug_base}-{count + 1}"
        return slug_base

    @staticmethod
    def render(text):
        if not text:
            return ""

        MarkdownRenderer._reset_heading_ids()

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
                f'<pre class="bg-gray-800 dark:bg-zinc-900 text-zinc-100 dark:text-zinc-100 p-4 rounded-lg my-4 overflow-x-auto border border-gray-700 dark:border-zinc-800 font-mono text-sm"><code class="language-{lang} text-inherit">{code}</code></pre>',
            )
            return placeholder

        text = re.sub(
            r"```(\w+)?\n(.*?)\n```",
            code_block_placeholder,
            text,
            flags=re.DOTALL,
        )

        # Inline code before emphasis so snake_case / ``rst`` spans are not
        # mangled by underscore italic (changelog uses both `code` and ``code``).
        inline_codes: list[str] = []

        def inline_code_placeholder(match):
            code = match.group(1)
            placeholder = f"[[IC{len(inline_codes)}]]"
            inline_codes.append(
                f'<code class="bg-gray-100 dark:bg-zinc-800 px-1.5 py-0.5 '
                f"rounded-sm text-pink-600 dark:text-pink-400 font-mono "
                f'text-[0.9em]">{code}</code>',
            )
            return placeholder

        # Double-backtick spans first (CommonMark / changelog RST-style).
        text = re.sub(r"``([^`]+)``", inline_code_placeholder, text)
        text = re.sub(r"`([^`]+)`", inline_code_placeholder, text)

        text = MarkdownRenderer._render_tables(text)

        # Horizontal Rules
        text = re.sub(
            r"^---+$",
            r'<hr class="my-8 border-t border-gray-200 dark:border-zinc-800">',
            text,
            flags=re.MULTILINE,
        )

        # Headers
        def heading_repl(level, classes):
            def repl(match):
                title = match.group(1)
                heading_id = MarkdownRenderer._heading_id(title, level)
                return (
                    f'<h{level} id="{heading_id}" class="{classes}">{title}</h{level}>'
                )

            return repl

        text = re.sub(
            r"^# (.*)$",
            heading_repl(
                1,
                "text-3xl font-bold mt-8 mb-4 text-gray-900 dark:text-zinc-100 scroll-mt-24",
            ),
            text,
            flags=re.MULTILINE,
        )
        text = re.sub(
            r"^## (.*)$",
            heading_repl(
                2,
                "text-2xl font-bold mt-8 mb-3 text-gray-900 dark:text-zinc-100 scroll-mt-24 border-b border-gray-200 dark:border-zinc-800 pb-2",
            ),
            text,
            flags=re.MULTILINE,
        )
        text = re.sub(
            r"^### (.*)$",
            heading_repl(
                3,
                "text-xl font-semibold mt-6 mb-2 text-gray-900 dark:text-zinc-100 scroll-mt-24",
            ),
            text,
            flags=re.MULTILINE,
        )
        text = re.sub(
            r"^#### (.*)$",
            heading_repl(
                4,
                "text-lg font-semibold mt-4 mb-2 text-gray-900 dark:text-zinc-100 scroll-mt-24",
            ),
            text,
            flags=re.MULTILINE,
        )

        # Bold and Italic (underscore italic requires word boundaries so
        # identifiers like local_hops_delta and api_extensions stay intact).
        text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", text)
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"\*(?!\s)(.+?)(?<!\s)\*", r"<em>\1</em>", text)
        text = re.sub(r"___(.+?)___", r"<strong><em>\1</em></strong>", text)
        text = re.sub(
            r"(?<!\w)__(?!\s)(.+?)(?<!\s)__(?!\w)", r"<strong>\1</strong>", text
        )
        text = re.sub(r"(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)", r"<em>\1</em>", text)

        # Strikethrough
        text = re.sub(r"~~(.*?)~~", r"<del>\1</del>", text)

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

        # Links (href sanitized to prevent javascript:/data: XSS)
        def link_repl(match):
            label, url = match.group(1), match.group(2)
            safe_url = _safe_href(url)
            return f'<a href="{html.escape(safe_url)}" class="text-blue-600 dark:text-blue-400 hover:underline" target="_blank" rel="noopener noreferrer">{label}</a>'

        text = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)",
            link_repl,
            text,
        )

        # Images (src sanitized)
        def img_repl(match):
            alt, src = match.group(1), match.group(2)
            safe_src = _safe_href(src)
            if safe_src == "#":
                return html.escape(match.group(0))
            return f'<div class="my-6"><img src="{html.escape(safe_src)}" alt="{alt}" class="max-w-full h-auto rounded-xl shadow-lg border border-gray-100 dark:border-zinc-800"></div>'

        text = re.sub(
            r"!\[([^\]]*)\]\(([^)]+)\)",
            img_repl,
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
            r"((?:^[*-] .*\n?)+)",
            unordered_list_repl,
            text,
            flags=re.MULTILINE,
        )

        def ordered_list_repl(match):
            items = match.group(0).strip().split("\n")
            html_items = ""
            for i in items:
                content = re.sub(r"^\d+\. ", "", i).strip()
                html_items += f'<li class="ml-4 mb-1 list-decimal text-gray-700 dark:text-zinc-300">{content}</li>'
            return f'<ol class="my-4 space-y-1">{html_items}</ol>'

        text = re.sub(
            r"((?:^\d+\. .*\n?)+)",
            ordered_list_repl,
            text,
            flags=re.MULTILINE,
        )

        # Paragraphs - double newline to p tag
        parts = text.split("\n\n")
        processed_parts = []
        for part in parts:
            part = part.strip()
            if not part:
                continue

            # If it's a placeholder for code block, don't wrap in <p>
            if re.fullmatch(r"\[\[(?:CB|IC)\d+\]\]", part):
                processed_parts.append(part)
                continue

            # If it already starts with a block tag, don't wrap in <p>
            if re.match(r"^<(h\d|ul|ol|li|blockquote|hr|div|table)", part):
                processed_parts.append(part)
            else:
                # Replace single newlines with <br> for line breaks within paragraphs
                part = part.replace("\n", "<br>")
                processed_parts.append(
                    f'<p class="my-4 leading-relaxed text-gray-800 dark:text-zinc-200">{part}</p>',
                )

        text = "\n".join(processed_parts)

        # Restore inline code then fenced blocks in one pass each (avoid O(n*m) loops).
        def _restore_inline(match):
            idx = int(match.group(1))
            if 0 <= idx < len(inline_codes):
                return inline_codes[idx]
            return match.group(0)

        def _restore_fenced(match):
            idx = int(match.group(1))
            if 0 <= idx < len(code_blocks):
                return code_blocks[idx]
            return match.group(0)

        text = re.sub(r"\[\[IC(\d+)\]\]", _restore_inline, text)
        text = re.sub(r"\[\[CB(\d+)\]\]", _restore_fenced, text)

        return text

    @staticmethod
    def _is_table_row(line):
        stripped = line.strip()
        return (
            stripped.startswith("|")
            and stripped.endswith("|")
            and stripped.count("|") >= 2
        )

    @staticmethod
    def _split_table_cells(line):
        return [cell.strip() for cell in line.strip().strip("|").split("|")]

    @staticmethod
    def _is_table_separator(line):
        if not MarkdownRenderer._is_table_row(line):
            return False
        cells = MarkdownRenderer._split_table_cells(line)
        if not cells:
            return False
        return all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)

    @staticmethod
    def _table_block_to_html(lines):
        header_cells = MarkdownRenderer._split_table_cells(lines[0])
        body_rows = [
            MarkdownRenderer._split_table_cells(row)
            for row in lines[2:]
            if MarkdownRenderer._is_table_row(row)
        ]
        thead = "".join(
            f'<th class="px-3 py-2 text-left font-bold">{cell}</th>'
            for cell in header_cells
        )
        tbody_rows = []
        for row in body_rows:
            padded = row + [""] * (len(header_cells) - len(row))
            cells = "".join(
                f'<td class="px-3 py-2 align-top">{cell}</td>'
                for cell in padded[: len(header_cells)]
            )
            tbody_rows.append(f"<tr>{cells}</tr>")
        tbody = "".join(tbody_rows)
        return (
            '<div class="overflow-x-auto my-6">'
            '<table class="w-full border-collapse text-sm">'
            f"<thead><tr>{thead}</tr></thead>"
            f"<tbody>{tbody}</tbody>"
            "</table></div>"
        )

    @staticmethod
    def _render_tables(text):
        lines = text.split("\n")
        out = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if (
                i + 1 < len(lines)
                and MarkdownRenderer._is_table_row(line)
                and MarkdownRenderer._is_table_separator(lines[i + 1])
            ):
                block = [line, lines[i + 1]]
                i += 2
                while i < len(lines) and MarkdownRenderer._is_table_row(lines[i]):
                    block.append(lines[i])
                    i += 1
                out.append(MarkdownRenderer._table_block_to_html(block))
            else:
                out.append(line)
                i += 1
        return "\n".join(out)
