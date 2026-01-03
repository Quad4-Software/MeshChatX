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
                <button
                    type="button"
                    class="secondary-chip !py-1 !px-3 !text-red-500 hover:!bg-red-50 dark:hover:!bg-red-900/20"
                    @click="resetAll"
                >
                    <MaterialDesignIcon icon-name="refresh" class="w-3.5 h-3.5" />
                    <span class="hidden sm:inline">{{ $t("tools.micron_editor.reset") }}</span>
                </button>
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

        <!-- Tab Bar -->
        <div
            class="flex items-center px-4 py-1 gap-1 border-b border-gray-200 dark:border-zinc-800 bg-slate-100 dark:bg-zinc-900 overflow-x-auto scrollbar-hide shrink-0"
        >
            <div
                v-for="(tab, index) in tabs"
                :key="tab.id"
                class="group flex items-center h-8 px-3 rounded-lg text-xs font-medium transition-colors cursor-pointer whitespace-nowrap"
                :class="[
                    activeTabIndex === index
                        ? 'bg-white dark:bg-zinc-800 text-teal-600 dark:text-teal-400 shadow-sm'
                        : 'text-gray-500 hover:bg-white/50 dark:hover:bg-zinc-800/50 hover:text-gray-700 dark:hover:text-zinc-300',
                ]"
                @click="activeTabIndex = index"
            >
                <span v-if="editingTabIndex !== index" @dblclick="startEditingTab(index)">{{ tab.name }}</span>
                <input
                    v-else
                    ref="tabInput"
                    v-model="editingTabName"
                    class="bg-transparent border-none focus:ring-0 w-20 p-0 text-inherit"
                    @blur="finishEditingTab"
                    @keyup.enter="finishEditingTab"
                    @click.stop
                />
                <button
                    v-if="tabs.length > 1"
                    class="ml-2 opacity-0 group-hover:opacity-100 hover:text-red-500 transition-opacity"
                    @click.stop="removeTab(index)"
                >
                    <MaterialDesignIcon icon-name="close" class="size-3" />
                </button>
            </div>
            <button
                class="flex items-center justify-center size-8 text-gray-400 hover:text-teal-500 transition-colors"
                @click="addTab"
            >
                <MaterialDesignIcon icon-name="plus" class="size-4" />
            </button>
        </div>

        <div class="flex-1 flex overflow-hidden">
            <!-- Editor Pane -->
            <div
                v-if="tabs.length > 0"
                :class="[
                    'flex-1 overflow-hidden flex flex-col',
                    isMobileView && !showEditor ? 'hidden' : '',
                    !isMobileView ? 'border-r border-gray-200 dark:border-zinc-800' : '',
                ]"
            >
                <textarea
                    ref="editorRef"
                    v-model="tabs[activeTabIndex].content"
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
import { micronStorage } from "../../js/MicronStorage";

export default {
    name: "MicronEditorPage",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            tabs: [],
            activeTabIndex: 0,
            renderedContent: "",
            showEditor: true,
            isMobileView: false,
            storageKey: "micron_editor_content",
            editingTabIndex: -1,
            editingTabName: "",
        };
    },
    watch: {
        activeTabIndex() {
            this.renderActiveTab();
        },
    },
    async mounted() {
        await this.loadContent();
        this.handleResize();
        window.addEventListener("resize", this.handleResize);
        this.renderActiveTab();
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
            this.renderActiveTab();
            this.saveContent();
        },
        renderActiveTab() {
            if (this.tabs.length === 0 || !this.tabs[this.activeTabIndex]) {
                this.renderedContent = "";
                return;
            }
            try {
                const parser = new MicronParser(true);
                this.renderedContent = parser.convertMicronToHtml(this.tabs[this.activeTabIndex].content);
            } catch (error) {
                console.error("Error rendering micron:", error);
                this.renderedContent = `<p style="color: red;">Error rendering: ${error.message}</p>`;
            }
        },
        toggleView() {
            this.showEditor = !this.showEditor;
        },
        async saveContent() {
            try {
                await micronStorage.saveTabs(this.tabs);
            } catch (error) {
                console.warn("Failed to save content to IndexedDB:", error);
            }
        },
        async loadContent() {
            try {
                const savedTabs = await micronStorage.loadTabs();
                if (savedTabs && savedTabs.length > 0) {
                    this.tabs = savedTabs;
                } else {
                    // Try to migrate from localStorage
                    const oldContent = localStorage.getItem(this.storageKey);
                    if (oldContent) {
                        this.tabs = [
                            {
                                id: Date.now(),
                                name: this.$t("tools.micron_editor.main_tab"),
                                content: oldContent,
                            },
                        ];
                        localStorage.removeItem(this.storageKey);
                        await micronStorage.saveTabs(this.tabs);
                    } else {
                        this.tabs = [this.createDefaultTab()];
                        await micronStorage.saveTabs(this.tabs);
                    }
                }
            } catch (error) {
                console.warn("Failed to load content from IndexedDB:", error);
                this.tabs = [this.createDefaultTab()];
            }
            this.activeTabIndex = 0;
        },
        createDefaultTab() {
            return {
                id: Date.now(),
                name: this.$t("tools.micron_editor.main_tab"),
                content: this.getDefaultContent(),
            };
        },
        addTab() {
            const newTab = {
                id: Date.now(),
                name: `${this.$t("tools.micron_editor.new_tab")} ${this.tabs.length + 1}`,
                content: "",
            };
            this.tabs.push(newTab);
            this.activeTabIndex = this.tabs.length - 1;
            this.saveContent();
        },
        removeTab(index) {
            if (confirm(this.$t("tools.micron_editor.confirm_delete_tab"))) {
                this.tabs.splice(index, 1);
                if (this.activeTabIndex >= this.tabs.length) {
                    this.activeTabIndex = Math.max(0, this.tabs.length - 1);
                }
                this.saveContent();
            }
        },
        startEditingTab(index) {
            this.editingTabIndex = index;
            this.editingTabName = this.tabs[index].name;
            this.$nextTick(() => {
                if (this.$refs.tabInput && this.$refs.tabInput[0]) {
                    this.$refs.tabInput[0].focus();
                }
            });
        },
        finishEditingTab() {
            if (this.editingTabIndex !== -1) {
                if (this.editingTabName.trim()) {
                    this.tabs[this.editingTabIndex].name = this.editingTabName.trim();
                }
                this.editingTabIndex = -1;
                this.saveContent();
            }
        },
        async resetAll() {
            if (confirm(this.$t("tools.micron_editor.confirm_reset"))) {
                await micronStorage.clearAll();
                this.tabs = [this.createDefaultTab()];
                this.activeTabIndex = 0;
                this.renderActiveTab();
                await this.saveContent();
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
            const content = this.tabs[this.activeTabIndex].content;
            const blob = new Blob([content], { type: "text/plain" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `${this.tabs[this.activeTabIndex].name.replace(/\s+/g, "_")}.mu`;
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

.scrollbar-hide::-webkit-scrollbar {
    display: none;
}
.scrollbar-hide {
    -ms-overflow-style: none;
    scrollbar-width: none;
}
</style>
