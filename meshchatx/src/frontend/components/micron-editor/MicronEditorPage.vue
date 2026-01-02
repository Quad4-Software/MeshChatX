<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-slate-50 dark:bg-zinc-950">
        <!-- Compact Header -->
        <div
            class="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-900/50 backdrop-blur-sm shrink-0"
        >
            <div class="flex items-center gap-3">
                <div class="bg-teal-100 dark:bg-teal-900/30 p-1.5 rounded-xl shrink-0">
                    <MaterialDesignIcon icon-name="code-tags" class="size-5 text-teal-600 dark:text-teal-400" />
                </div>
                <h1
                    class="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider hidden sm:block truncate"
                >
                    {{ $t("tools.micron_editor.title") }}
                </h1>
            </div>
            <div class="flex items-center gap-2">
                <button type="button" class="secondary-chip !py-1 !px-3" @click="downloadFile">
                    <MaterialDesignIcon icon-name="download" class="w-3.5 h-3.5" />
                    <span class="hidden sm:inline">{{ $t("tools.micron_editor.download") }}</span>
                </button>
                <button v-if="isMobileView" type="button" class="primary-chip !py-1 !px-3" @click="toggleView">
                    <MaterialDesignIcon :icon-name="showEditor ? 'eye' : 'pencil'" class="w-3.5 h-3.5" />
                    {{ showEditor ? $t("tools.micron_editor.view_preview") : $t("tools.micron_editor.edit") }}
                </button>
            </div>
        </div>

        <div class="flex-1 flex overflow-hidden">
            <!-- Editor Pane -->
            <div
                :class="[
                    'flex-1 overflow-hidden flex flex-col',
                    isMobileView && !showEditor ? 'hidden' : '',
                    !isMobileView ? 'border-r border-gray-200 dark:border-zinc-800' : '',
                ]"
            >
                <textarea
                    ref="editorRef"
                    v-model="content"
                    class="flex-1 w-full bg-white dark:bg-zinc-900 text-gray-900 dark:text-white p-4 font-mono text-sm resize-none focus:outline-none"
                    :placeholder="$t('tools.micron_editor.placeholder')"
                    @input="handleInput"
                ></textarea>
            </div>

            <!-- Preview Pane (Always dark to match NomadNet browser vibe) -->
            <div
                :class="[
                    'flex-1 overflow-hidden flex flex-col bg-zinc-950',
                    isMobileView && showEditor ? 'hidden' : '',
                ]"
            >
                <!-- eslint-disable vue/no-v-html -->
                <div
                    ref="previewRef"
                    class="flex-1 overflow-auto text-zinc-100 p-4 font-mono text-sm whitespace-pre-wrap break-words nodeContainer"
                    v-html="renderedContent"
                ></div>
                <!-- eslint-enable vue/no-v-html -->
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import MicronParser from "micron-parser";

export default {
    name: "MicronEditorPage",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            content: "",
            renderedContent: "",
            showEditor: true,
            isMobileView: false,
            storageKey: "micron_editor_content",
        };
    },
    mounted() {
        this.loadContent();
        this.handleResize();
        window.addEventListener("resize", this.handleResize);
        this.handleInput();
    },
    beforeUnmount() {
        window.removeEventListener("resize", this.handleResize);
    },
    methods: {
        handleResize() {
            this.isMobileView = window.innerWidth < 1024;
            if (!this.isMobileView) {
                this.showEditor = true;
            }
        },
        handleInput() {
            try {
                // Always use dark mode for parser since preview pane is now always dark
                // to match the NomadNet browser's classic appearance.
                const parser = new MicronParser(true);
                this.renderedContent = parser.convertMicronToHtml(this.content);
            } catch (error) {
                console.error("Error rendering micron:", error);
                this.renderedContent = `<p style="color: red;">Error rendering: ${error.message}</p>`;
            }
            this.saveContent();
        },
        toggleView() {
            this.showEditor = !this.showEditor;
        },
        saveContent() {
            try {
                localStorage.setItem(this.storageKey, this.content);
            } catch (error) {
                console.warn("Failed to save content to localStorage:", error);
            }
        },
        loadContent() {
            try {
                const saved = localStorage.getItem(this.storageKey);
                if (saved) {
                    this.content = saved;
                } else {
                    this.content = this.getDefaultContent();
                }
            } catch (error) {
                console.warn("Failed to load content from localStorage:", error);
                this.content = this.getDefaultContent();
            }
        },
        getDefaultContent() {
            const b = "`";
            return `${b}Ffd0
${b}=
            _                                                           _
           (_)                                                         (_)
  _ __ ___  _  ___ _ __ ___  _ __ ______ _ __   __ _ _ __ ___  ___ _ __ _ ___
 | '_ \` _ \\| |/ __| '__/ _ \\| '_ \\______| '_ \\ / _\` | '__/ __|/ _ \\ '__| / __|
 | | | | | | | (__| | | (_) | | | |     | |_) | (_| | |  \\__ \\\\  __/ |_ | \\__ \\\\
 |_| |_| |_|_|\\___|_|  \\___/|_| |_|     | .__/ \\__,_|_|  |___/\\___|_(_)| |___/
                                        | |                           _/ |
                                        |_|                          |__/

${b}=
${b}f

${b}!Welcome to Micron Editor${b}!
-
Micron is a lightweight, terminal-friendly monospace markdown format used in Reticulum applications.

${b}!With Micron, you can${b}${b}:

${b}c Align${b}b

${b}r text,

${b}a
${b}c
set ${b}B005 backgrounds, ${b}b and ${b}*${b} ${b}B777${b}Ffffcombine any number of${b}f${b}b${b}_${b}_ ${b}Ff00f${b}Ff80o${b}Ffd0r${b}F9f0m${b}F0f2a${b}F0fdt${b}F07ft${b}F43fi${b}F70fn${b}Fe0fg ${b}ftags.
${b}${b}

>Getting Started

Start editing your Micron markup in the editor pane. The preview will update automatically.

>Formatting

Text can be ${b}!bold${b}! by using \\${b}!, \\${b}_, and \\${b}*.

>Colors

Foreground colors: ${b}Ff00${b}Ff80o${b}Ffd0r${b}F9f0m${b}F0f2a${b}F0fdt${b}F07ft${b}F43fi${b}F70fn${b}Fe0fg${b}f
Background colors: ${b}Bf00${b}Bf80o${b}Bfd0r${b}B9f0m${b}B0f2a${b}B0fdt${b}B07ft${b}B43fi${b}B70fn${b}Be0fg${b}b

>Links

Create links with \\${b}[ tag: ${b}_${b}[Example Link${b}example.com]${b}]${b}_

>Literals

Use \\${b}= to start/end literal blocks that won't be interpreted.

${b}=
This is a literal block
${b}=
`;
        },
        downloadFile() {
            const blob = new Blob([this.content], { type: "text/plain" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "micron.mu";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        },
    },
};
</script>

<style scoped>
.nodeContainer {
    font-family:
        Roboto Mono Nerd Font,
        monospace;
    line-height: normal;
}

:deep(.Mu-nl) {
    cursor: pointer;
}
:deep(.Mu-mnt) {
    display: inline-block;
    width: 0.6em;
    text-align: center;
    white-space: pre;
    text-decoration: inherit;
}
:deep(.Mu-mws) {
    text-decoration: inherit;
    display: inline-block;
}

:deep(a:hover) {
    text-decoration: underline;
}
</style>
