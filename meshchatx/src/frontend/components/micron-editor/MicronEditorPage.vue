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
                <div class="flex flex-col">
                    <h1
                        class="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider hidden sm:block truncate leading-tight"
                    >
                        {{ $t("tools.micron_editor.title") }}
                    </h1>
                    <a
                        href="https://git.quad4.io/RFnexus"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="text-[10px] text-gray-500 hover:text-teal-500 transition-colors hidden sm:block leading-tight"
                    >
                        {{ $t("tools.micron_editor.parser_by") }} RFnexus
                    </a>
                </div>
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
                    <span class="hidden sm:inline">{{ $t("tools.micron_editor.save") }}</span>
                </button>
                <div class="relative">
                    <button type="button" class="primary-chip !py-1 !px-3" @click="togglePublishMenu">
                        <MaterialDesignIcon icon-name="publish" class="w-3.5 h-3.5" />
                        <span class="hidden sm:inline">Publish</span>
                    </button>
                    <div
                        v-if="showPublishMenu"
                        v-click-outside="() => (showPublishMenu = false)"
                        class="absolute right-0 top-full mt-1 w-64 bg-white dark:bg-zinc-800 rounded-xl shadow-xl border border-gray-200 dark:border-zinc-700 z-50 py-2"
                    >
                        <div
                            class="px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400"
                        >
                            Publish to Mesh Server
                        </div>
                        <div v-if="pageNodes.length === 0" class="px-3 py-2 text-xs text-gray-500 dark:text-gray-400">
                            No mesh servers available.
                            <router-link to="/mesh-server" class="text-blue-500 hover:underline"
                                >Create one</router-link
                            >
                        </div>
                        <button
                            v-for="pn in pageNodes"
                            :key="pn.node_id"
                            class="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-zinc-700 flex items-center gap-2 transition-colors"
                            @click="publishToNode(pn)"
                        >
                            <div
                                class="w-2 h-2 rounded-full shrink-0"
                                :class="pn.running ? 'bg-green-500' : 'bg-gray-400'"
                            ></div>
                            <span class="truncate text-gray-900 dark:text-white">{{ pn.name }}</span>
                        </button>
                        <div class="border-t border-gray-200 dark:border-zinc-700 mt-1 pt-1">
                            <button
                                class="w-full text-left px-3 py-2 text-xs text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-zinc-700 transition-colors"
                                @click="publishAllToNode"
                            >
                                Publish all tabs to server...
                            </button>
                        </div>
                    </div>
                </div>
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
import DialogUtils from "../../js/DialogUtils";

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
            showPublishMenu: false,
            pageNodes: [],
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
                            this.createGuideTab(Date.now() + 1),
                        ];
                        localStorage.removeItem(this.storageKey);
                        await micronStorage.saveTabs(this.tabs);
                    } else {
                        this.tabs = [this.createDefaultTab(), this.createGuideTab(Date.now() + 1)];
                        await micronStorage.saveTabs(this.tabs);
                    }
                }
            } catch (error) {
                console.warn("Failed to load content from IndexedDB:", error);
                this.tabs = [this.createDefaultTab(), this.createGuideTab(Date.now() + 1)];
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
        createGuideTab(id = Date.now()) {
            return {
                id: id,
                name: this.$t("tools.micron_editor.guide_tab"),
                content: this.getGuideContent(),
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
        async removeTab(index) {
            if (await DialogUtils.confirm(this.$t("tools.micron_editor.confirm_delete_tab"))) {
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
            if (await DialogUtils.confirm(this.$t("tools.micron_editor.confirm_reset"))) {
                await micronStorage.clearAll();
                this.tabs = [this.createDefaultTab(), this.createGuideTab(Date.now() + 1)];
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
        getGuideContent() {
            const b = "`";
            return `-∿
<

${b}c${b}!Hello!${b}! This is output from ${b}*micron${b}*
Micron generates formatted text for your terminal
${b}a


-∿
<


Nomad Network supports a simple and functional markup language called ${b}*micron${b}*. If you are familiar with ${b}*markdown${b}* or ${b}*HTML${b}*, you will feel right at home writing pages with micron.

With micron you can easily create structured documents and pages with formatting, colors, glyphs and icons, ideal for display in terminals.

>>Recommendations and Requirements

While micron can output formatted text to even the most basic terminal, there's a few capabilities your terminal ${b}*must${b}* support to display micron output correctly, and some that, while not strictly necessary, make the experience a lot better.

Formatting such as ${b}_underline${b}_, ${b}!bold${b}! or ${b}*italics${b}* will be displayed if your terminal supports it.

If you are having trouble getting micron output to display correctly, try using ${b}*gnome-terminal${b}* or ${b}*alacritty${b}*, which should work with all formatting options out of the box. Most other terminals will work fine as well, but you might have to change some settings to get certain formatting to display correctly.

>>>Encoding

All micron sources are intepreted as UTF-8, and micron assumes it can output UTF-8 characters to the terminal. If your terminal does not support UTF-8, output will be faulty.

>>>Colors

Shading and coloring text and backgrounds is integral to micron output, and while micron will attempt to gracefully degrade output even to 1-bit terminals, you will get the best output with terminals supporting at least 256 colors. True-color support is recommended.

>>>Terminal Font

While any unicode capable font can be used with micron, it's highly recommended to use a ${b}*"Nerd Font"${b}* (see https://www.nerdfonts.com/), which will add a lot of extra glyphs and icons to your output.

> A Few Demo Outputs

${b}F222${b}Bddd

${b}cWith micron, you can control layout and presentation
${b}a

${b}${b}

${b}B33f

You can change background ...

${b}${b}

${b}B393

${b}r${b}F320... and foreground colors${b}f
${b}a

${b}b

If you want to make a break, horizontal dividers can be inserted. They can be plain, like the one below this text, or you can style them with unicode characters and glyphs, like the wavy divider in the beginning of this document.

-

${b}cText can be ${b}_underlined${b}_, ${b}!bold${b}! or ${b}*italic${b}*.

You can also ${b}_${b}*${b}!B5d5${b}F222combine${b}f${b}b${b}_ ${b}_${b}Ff00f${b}Ff80o${b}Ffd0r${b}F9f0m${b}F0f2a${b}F0fdt${b}F07ft${b}F43fi${b}F70fn${b}Fe0fg${b}${b} for some fabulous effects.
${b}a


>>>Sections and Headings

You can define an arbitrary number of sections and sub sections, each with their own named headings. Text inside sections will be automatically indented.

-

If you place a divider inside a section, it will adhere to the section indents.

>>>>>
If no heading text is defined, the section will appear as a sub-section without a header. This can be useful for creating indented blocks of text, like this one.

>Micron tags

Tags are used to format text with micron. Some tags can appear anywhere in text, and some must appear at the beginning of a line. If you need to write text that contains a sequence that would be interpreted as a tag, you can escape it with the character \\.

In the following sections, the different tags will be introduced. Any styling set within micron can be reset to the default style by using the special \\${b}\\${b} tag anywhere in the markup, which will immediately remove any formatting previously specified.

>>Alignment

To control text alignment use the tag \\${b}c to center text, \\${b}l to left-align, \\${b}r to right-align, and \\${b}a to return to the default alignment of the document. Alignment tags must appear at the beginning of a line. Here is an example:

${b}Faaa
${b}=
${b}cThis line will be centered.
So will this.
${b}aThe alignment has now been returned to default.
${b}rThis will be aligned to the right
${b}${b}
${b}=
${b}${b}

The above markup produces the following output:

${b}Faaa${b}B333

${b}cThis line will be centered.
So will this.

${b}aThe alignment has now been returned to default.

${b}rThis will be aligned to the right

${b}${b}


>>Formatting

Text can be formatted as ${b}!bold${b}! by using the \\${b}! tag, ${b}_underline${b}_ by using the \\${b}_ tag and ${b}*italic${b}* by using the \\${b}* tag.

Here's an example of formatting text:

${b}Faaa
${b}=
We shall soon see ${b}!bold${b}! paragraphs of text decorated with ${b}_underlines${b}_ and ${b}*italics${b}*. Some even dare ${b}!${b}*${b}_combine${b}${b} them!
${b}=
${b}${b}

The above markup produces the following output:

${b}Faaa${b}B333

We shall soon see ${b}!bold${b}! paragraphs of text decorated with ${b}_underlines${b}_ and ${b}*italics${b}*. Some even dare ${b}!${b}*${b}_combine${b}!${b}*${b}_ them!

${b}${b}


>>Sections

To create sections and subsections, use the > tag. This tag must be placed at the beginning of a line. To specify a sub-section of any level, use any number of > tags. If text is placed after a > tag, it will be used as a heading.

Here is an example of sections:

${b}Faaa
${b}=
>High Level Stuff
This is a section. It contains this text.

>>Another Level
This is a sub section.

>>>Going deeper
A sub sub section. We could continue, but you get the point.

>>>>
Wait! It's worth noting that we can also create sections without headings. They look like this.
${b}=
${b}${b}

The above markup produces the following output:

${b}Faaa${b}B333
>High Level Stuff
This is a section. It contains this text.

>>Another Level
This is a sub section.

>>>Going deeper
A sub sub section. We could continue, but you get the point.

>>>>
Wait! It's worth noting that we can also create sections without headings. They look like this.
${b}${b}


>Colors

Foreground colors can be specified with the \\${b}F tag, followed by three hexadecimal characters. To return to the default foreground color, use the \\${b}f tag. Background color is specified in the same way, but by using the \\${b}B and \\${b}b tags.

Here's a few examples:

${b}Faaa
${b}=
You can use ${b}B5d5${b}F222 color ${b}f${b}b ${b}Ff00f${b}Ff80o${b}Ffd0r${b}F9f0m${b}F0f2a${b}F0fdt${b}F07ft${b}F43fi${b}F70fn${b}Fe0fg${b}f for some fabulous effects.
${b}=
${b}${b}

The above markup produces the following output:

${b}Faaa${b}B333

You can use ${b}B5d5${b}F222 color ${b}f${b}B333 ${b}Ff00f${b}Ff80o${b}Ffd0r${b}F9f0m${b}F0f2a${b}F0fdt${b}F07ft${b}F43fi${b}F70fn${b}Fe0fg${b}f for some fabulous effects.

${b}${b}


>Links

Links to pages, files or other resources can be created with the \\${b}[ tag, which should always be terminated with a closing ]. You can create links with and without labels, it is up to you to control the formatting of links with other tags. Although not strictly necessary, it is good practice to at least format links with underlining.

Here's a few examples:

${b}Faaa
${b}=
Here is a link without any label: ${b}[72914442a3689add83a09a767963f57c:/page/index.mu]

This is a ${b}[labeled link${b}72914442a3689add83a09a767963f57c:/page/index.mu] to the same page, but it's hard to see if you don't know it

Here is ${b}F00a${b}_${b}[a more visible link${b}72914442a3689add83a09a767963f57c:/page/index.mu]${b}_${b}f
${b}=
${b}${b}

The above markup produces the following output:

${b}Faaa${b}B333

Here is a link without any label: ${b}[72914442a3689add83a09a767963f57c:/page/index.mu]

This is a ${b}[labeled link${b}72914442a3689add83a09a767963f57c:/page/index.mu] to the same page, but it's hard to see if you don't know it

Here is ${b}F00f${b}_${b}[a more visible link${b}72914442a3689add83a09a767963f57c:/page/index.mu]${b}_${b}f

${b}${b}

When links like these are displayed in the built-in browser, clicking on them or activating them using the keyboard will cause the browser to load the specified URL.

>Fields & Requests

Nomad Network let's you use simple input fields for submitting data to node-side applications. Submitted data, along with other session variables will be available to the node-side script / program as environment variables.

>>Request Links

Links can contain request variables and a list of fields to submit to the node-side application. You can include all fields on the page, only specific ones, and any number of request variables. To simply submit all fields on a page to a specified node-side page, create a link like this:

${b}Faaa
${b}=
${b}[Submit Fields${b}:/page/fields.mu${b}*]
${b}=
${b}${b}

Note the ${b}!*${b}! following the extra ${b}!\\${b}${b}! at the end of the path. This ${b}!*${b}! denotes ${b}*all fields${b}*. You can also specify a list of fields to include:

${b}Faaa
${b}=
${b}[Submit Fields${b}:/page/fields.mu${b}username|auth_token]
${b}=
${b}${b}

If you want to include pre-set variables, you can do it like this:

${b}Faaa
${b}=
${b}[Query the System${b}:/page/fields.mu${b}username|auth_token|action=view|amount=64]
${b}=
${b}${b}

>> Fields

Here's an example of creating a field. We'll create a field named ${b}!user_input${b}! and fill it with the text ${b}!Pre-defined data${b}!. Note that we are using background color tags to make the field more visible to the user:

${b}Faaa
${b}=
A simple input field: ${b}B444${b}<user_input${b}Pre-defined data>${b}b
${b}=
${b}${b}

You must always set a field ${b}*name${b}*, but you can of course omit the pre-defined value of the field:

${b}Faaa
${b}=
An empty input field: ${b}B444${b}<demo_empty${b}>${b}b
${b}=
${b}${b}

You can set the size of the field like this:

${b}Faaa
${b}=
A sized input field:  ${b}B444${b}<16|with_size${b}>${b}b
${b}=
${b}${b}

It is possible to mask fields, for example for use with passwords and similar:

${b}Faaa
${b}=
A masked input field: ${b}B444${b}<!|masked_demo${b}hidden text>${b}b
${b}=
${b}${b}

And you can of course control all parameters at the same time:

${b}Faaa
${b}=
Full control: ${b}B444${b}<!32|all_options${b}hidden text>${b}b
${b}=
${b}${b}

Collecting the above markup produces the following output:

${b}Faaa${b}B333

A simple input field: ${b}B444${b}<user_input${b}Pre-defined data>${b}B333

An empty input field: ${b}B444${b}<demo_empty${b}>${b}B333

A sized input field:  ${b}B444${b}<16|with_size${b}>${b}B333

A masked input field: ${b}B444${b}<!|masked_demo${b}hidden text>${b}B333

Full control: ${b}B444${b}<!32|all_options${b}hidden text>${b}B333
${b}b
>>> Checkboxes

In addition to text fields, Checkboxes are another way of submitting data. They allow the user to make a single selection or select multiple options.

${b}Faaa
${b}=
${b}<?|field_name|value${b}>${b}b Label Text${b}
${b}=
When the checkbox is checked, it's field will be set to the provided value. If there are multiple checkboxes that share the same field name, the checked values will be concatenated when they are sent to the node by a comma.
${b}${b}

${b}B444${b}<?|sign_up|1${b}>${b}b Sign me up${b}

You can also pre-check both checkboxes and radio groups by appending a |* after the field value.

${b}B444${b}<?|checkbox|1|*${b}>${b}b Pre-checked checkbox${b}

>>> Radio groups

Radio groups are another input that lets the user chose from a set of options. Unlike checkboxes, radio buttons with the same field name are mutually exclusive.

Example:

${b}=
${b}B900${b}<^|color|Red${b}>${b}b  Red

${b}B090${b}<^|color|Green${b}>${b}b Green

${b}B009${b}<^|color|Blue${b}>${b}b Blue
${b}=

will render:

${b}B900${b}<^|color|Red${b}>${b}b  Red

${b}B090${b}<^|color|Green${b}>${b}b Green

${b}B009${b}<^|color|Blue${b}>${b}b Blue

In this example, when the data is submitted, ${b}B444${b} field_color${b}b will be set to whichever value from the list was selected.

${b}${b}

>Comments

You can insert comments that will not be displayed in the output by starting a line with the # character.

Here's an example:

${b}Faaa
${b}=
# This line will not be displayed
This line will
${b}=
${b}${b}

The above markup produces the following output:

${b}Faaa${b}B333

# This line will not be displayed
This line will

${b}${b}


>Literals

To display literal content, for example source-code, or blocks of text that should not be interpreted by micron, you can use literal blocks, specified by the \\${b}= tag. Below is the source code of this entire document, presented as a literal block.

-

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
        async togglePublishMenu() {
            this.showPublishMenu = !this.showPublishMenu;
            if (this.showPublishMenu) {
                try {
                    const response = await window.axios.get("/api/v1/page-nodes");
                    this.pageNodes = response.data;
                } catch {
                    this.pageNodes = [];
                }
            }
        },
        async publishToNode(node) {
            const tab = this.tabs[this.activeTabIndex];
            const pageName = tab.name.replace(/\s+/g, "_");
            try {
                await window.axios.post(`/api/v1/page-nodes/${node.node_id}/pages`, {
                    name: pageName,
                    content: tab.content,
                });
                this.showPublishMenu = false;
                DialogUtils.alert(`Published "${pageName}.mu" to ${node.name}`);
            } catch (e) {
                DialogUtils.alert(e.response?.data?.message || "Failed to publish page");
            }
        },
        async publishAllToNode() {
            if (this.pageNodes.length === 0) return;

            const nodeNames = this.pageNodes.map((n) => n.name);
            const nodeName = prompt("Enter server name to publish all tabs to:\n\nAvailable: " + nodeNames.join(", "));
            if (!nodeName) return;

            const node = this.pageNodes.find((n) => n.name === nodeName);
            if (!node) {
                DialogUtils.alert("Server not found: " + nodeName);
                return;
            }

            let published = 0;
            for (const tab of this.tabs) {
                const pageName = tab.name.replace(/\s+/g, "_");
                try {
                    await window.axios.post(`/api/v1/page-nodes/${node.node_id}/pages`, {
                        name: pageName,
                        content: tab.content,
                    });
                    published++;
                } catch {
                    console.error(`Failed to publish tab: ${tab.name}`);
                }
            }
            this.showPublishMenu = false;
            DialogUtils.alert(`Published ${published}/${this.tabs.length} tabs to ${node.name}`);
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
