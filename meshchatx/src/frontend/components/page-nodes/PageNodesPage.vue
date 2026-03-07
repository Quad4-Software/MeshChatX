<template>
    <div
        class="flex flex-col flex-1 overflow-hidden min-w-0 bg-gradient-to-br from-slate-50 via-slate-100 to-white dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900"
    >
        <div class="flex-1 overflow-y-auto w-full px-4 md:px-8 py-6">
            <div class="space-y-4 w-full max-w-5xl mx-auto">
                <div class="glass-card space-y-5">
                    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div class="space-y-2">
                            <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                                Reticulum Content Serving
                            </div>
                            <div class="text-2xl font-semibold text-gray-900 dark:text-white">Mesh Server</div>
                            <div class="text-sm text-gray-600 dark:text-gray-300">
                                Serve Micron pages and files directly over the Reticulum mesh. Each server gets its own
                                identity and destination address.
                            </div>
                        </div>
                        <button
                            type="button"
                            class="primary-chip px-4 py-2 text-sm shrink-0"
                            @click="showCreateDialog = true"
                        >
                            <MaterialDesignIcon icon-name="plus" class="w-4 h-4" />
                            Create Node
                        </button>
                    </div>
                </div>

                <div v-if="loading" class="glass-card text-center py-12">
                    <div class="text-gray-500 dark:text-gray-400">Loading nodes...</div>
                </div>

                <div v-else-if="nodes.length === 0" class="glass-card text-center py-12">
                    <MaterialDesignIcon icon-name="server-network" class="w-12 h-12 mx-auto mb-4 text-gray-400" />
                    <div class="text-gray-600 dark:text-gray-400 mb-2">No mesh servers yet</div>
                    <div class="text-sm text-gray-500 dark:text-gray-500">
                        Create a server to start serving Micron pages over the mesh.
                    </div>
                </div>

                <div v-else class="space-y-3">
                    <div
                        v-for="node in nodes"
                        :key="node.node_id"
                        class="glass-card space-y-4 cursor-pointer hover:border-blue-400 dark:hover:border-blue-500 transition"
                        @click="selectNode(node)"
                    >
                        <div class="flex items-center justify-between">
                            <div class="flex items-center gap-3">
                                <div
                                    class="w-3 h-3 rounded-full"
                                    :class="node.running ? 'bg-green-500' : 'bg-gray-400'"
                                ></div>
                                <div>
                                    <div class="font-semibold text-gray-900 dark:text-white">{{ node.name }}</div>
                                    <div
                                        v-if="node.destination_hash"
                                        class="text-xs font-mono text-gray-500 dark:text-gray-400"
                                    >
                                        {{ node.destination_hash }}
                                    </div>
                                </div>
                            </div>
                            <div class="flex items-center gap-2">
                                <span class="text-xs text-gray-500 dark:text-gray-400">
                                    {{ node.pages.length }} pages, {{ node.files.length }} files
                                </span>
                                <button
                                    v-if="!node.running"
                                    class="primary-chip !py-1 !px-3 !text-xs"
                                    @click.stop="startNode(node.node_id)"
                                >
                                    Start
                                </button>
                                <button
                                    v-else
                                    class="secondary-chip !py-1 !px-3 !text-xs !text-red-500 hover:!bg-red-50 dark:hover:!bg-red-900/20"
                                    @click.stop="stopNode(node.node_id)"
                                >
                                    Stop
                                </button>
                                <button
                                    v-if="node.running"
                                    class="secondary-chip !py-1 !px-3 !text-xs"
                                    @click.stop="announceNode(node.node_id)"
                                >
                                    Announce
                                </button>
                                <button
                                    v-if="node.running && node.destination_hash"
                                    class="secondary-chip !py-1 !px-3 !text-xs"
                                    @click.stop="viewNode(node)"
                                >
                                    <MaterialDesignIcon icon-name="eye" class="w-3.5 h-3.5" />
                                    View
                                </button>
                                <button
                                    class="secondary-chip !py-1 !px-3 !text-xs !text-red-500 hover:!bg-red-50 dark:hover:!bg-red-900/20"
                                    @click.stop="deleteNode(node.node_id)"
                                >
                                    <MaterialDesignIcon icon-name="delete" class="w-3.5 h-3.5" />
                                </button>
                            </div>
                        </div>

                        <div v-if="node.stats" class="flex gap-4 text-xs text-gray-500 dark:text-gray-400">
                            <span>{{ node.stats.pages_served }} pages served</span>
                            <span>{{ node.stats.files_served }} files served</span>
                            <span>{{ node.stats.links_established }} links</span>
                        </div>
                    </div>
                </div>

                <!-- Selected Node Detail -->
                <div v-if="selectedNode" class="glass-card space-y-5">
                    <div class="flex items-center justify-between">
                        <div class="text-lg font-semibold text-gray-900 dark:text-white">
                            {{ selectedNode.name }}
                        </div>
                        <div class="flex items-center gap-2">
                            <button class="secondary-chip !py-1 !px-3 !text-xs" @click="showRenameDialog = true">
                                Rename
                            </button>
                            <button class="secondary-chip !py-1 !px-3 !text-xs" @click="selectedNode = null">
                                <MaterialDesignIcon icon-name="close" class="w-3.5 h-3.5" />
                            </button>
                        </div>
                    </div>

                    <div
                        v-if="selectedNode.destination_hash"
                        class="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                    >
                        <div class="flex items-center justify-between mb-1">
                            <div class="text-xs font-bold uppercase tracking-wider">Destination Hash</div>
                            <button
                                v-if="selectedNode.running"
                                class="primary-chip !py-0.5 !px-2 !text-xs"
                                @click="viewNode(selectedNode)"
                            >
                                <MaterialDesignIcon icon-name="eye" class="w-3 h-3" />
                                View in Browser
                            </button>
                        </div>
                        <div class="font-mono text-sm select-all">{{ selectedNode.destination_hash }}</div>
                    </div>

                    <!-- Tabs: Pages / Files -->
                    <div class="flex gap-2 border-b border-gray-200 dark:border-zinc-700">
                        <button
                            :class="[
                                detailTab === 'pages'
                                    ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
                                    : 'text-gray-600 dark:text-gray-400',
                                'px-4 py-2 font-semibold transition text-sm',
                            ]"
                            @click="detailTab = 'pages'"
                        >
                            Pages ({{ selectedNode.pages.length }})
                        </button>
                        <button
                            :class="[
                                detailTab === 'files'
                                    ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
                                    : 'text-gray-600 dark:text-gray-400',
                                'px-4 py-2 font-semibold transition text-sm',
                            ]"
                            @click="detailTab = 'files'"
                        >
                            Files ({{ selectedNode.files.length }})
                        </button>
                    </div>

                    <!-- Pages Tab -->
                    <div v-if="detailTab === 'pages'" class="space-y-3">
                        <div class="flex gap-2">
                            <input
                                v-model="newPageName"
                                type="text"
                                placeholder="Page name (e.g. index)"
                                class="input-field flex-1"
                                @keyup.enter="addPage"
                            />
                            <button class="primary-chip !py-1 !px-3 !text-xs" @click="addPage">
                                <MaterialDesignIcon icon-name="plus" class="w-3.5 h-3.5" />
                                Add Page
                            </button>
                        </div>

                        <div
                            v-if="selectedNode.pages.length === 0"
                            class="text-sm text-gray-500 dark:text-gray-400 py-4 text-center"
                        >
                            No pages yet. Add one or publish from the Micron Editor.
                        </div>

                        <div
                            v-for="page in selectedNode.pages"
                            :key="page"
                            class="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-zinc-800/50 border border-gray-200 dark:border-zinc-700"
                        >
                            <div class="flex items-center gap-2">
                                <MaterialDesignIcon icon-name="file-document-outline" class="w-4 h-4 text-teal-500" />
                                <span class="text-sm font-mono text-gray-900 dark:text-white">{{ page }}</span>
                            </div>
                            <div class="flex items-center gap-2">
                                <button class="secondary-chip !py-0.5 !px-2 !text-xs" @click="editPage(page)">
                                    Edit
                                </button>
                                <button
                                    class="secondary-chip !py-0.5 !px-2 !text-xs !text-red-500"
                                    @click="deletePage(page)"
                                >
                                    <MaterialDesignIcon icon-name="delete" class="w-3 h-3" />
                                </button>
                            </div>
                        </div>

                        <!-- Page editor -->
                        <div v-if="editingPage" class="space-y-2">
                            <div class="flex items-center justify-between">
                                <div class="text-sm font-semibold text-gray-900 dark:text-white">
                                    Editing: {{ editingPage }}
                                </div>
                                <div class="flex gap-2">
                                    <button class="primary-chip !py-1 !px-3 !text-xs" @click="savePage">Save</button>
                                    <button class="secondary-chip !py-1 !px-3 !text-xs" @click="editingPage = null">
                                        Cancel
                                    </button>
                                </div>
                            </div>
                            <textarea
                                v-model="editingPageContent"
                                class="w-full h-64 bg-white dark:bg-zinc-900 text-gray-900 dark:text-white p-3 font-mono text-sm rounded-lg border border-gray-200 dark:border-zinc-700 resize-y focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                            ></textarea>
                        </div>
                    </div>

                    <!-- Files Tab -->
                    <div v-if="detailTab === 'files'" class="space-y-3">
                        <div class="flex gap-2">
                            <input ref="fileInput" type="file" class="hidden" @change="uploadFile" />
                            <button class="primary-chip !py-1 !px-3 !text-xs" @click="$refs.fileInput.click()">
                                <MaterialDesignIcon icon-name="upload" class="w-3.5 h-3.5" />
                                Upload File
                            </button>
                        </div>

                        <div
                            v-if="selectedNode.files.length === 0"
                            class="text-sm text-gray-500 dark:text-gray-400 py-4 text-center"
                        >
                            No files yet. Upload files to serve over the mesh.
                        </div>

                        <div
                            v-for="file in selectedNode.files"
                            :key="file.name"
                            class="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-zinc-800/50 border border-gray-200 dark:border-zinc-700"
                        >
                            <div class="flex items-center gap-2">
                                <MaterialDesignIcon icon-name="file-outline" class="w-4 h-4 text-blue-500" />
                                <span class="text-sm font-mono text-gray-900 dark:text-white">{{ file.name }}</span>
                                <span class="text-xs text-gray-500 dark:text-gray-400">{{
                                    formatFileSize(file.size)
                                }}</span>
                            </div>
                            <button
                                class="secondary-chip !py-0.5 !px-2 !text-xs !text-red-500"
                                @click="deleteFile(file.name)"
                            >
                                <MaterialDesignIcon icon-name="delete" class="w-3 h-3" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Create Node Dialog -->
        <div
            v-if="showCreateDialog"
            class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            @click.self="showCreateDialog = false"
        >
            <div class="bg-white dark:bg-zinc-900 rounded-2xl p-6 w-full max-w-md mx-4 shadow-xl space-y-4">
                <div class="text-lg font-semibold text-gray-900 dark:text-white">Create Mesh Server</div>
                <div>
                    <label class="glass-label">Server Name</label>
                    <input
                        v-model="createNodeName"
                        type="text"
                        placeholder="My Mesh Server"
                        class="input-field"
                        @keyup.enter="createNode"
                    />
                </div>
                <div class="flex justify-end gap-2">
                    <button class="secondary-chip !py-1.5 !px-4 !text-sm" @click="showCreateDialog = false">
                        Cancel
                    </button>
                    <button class="primary-chip !py-1.5 !px-4 !text-sm" @click="createNode">Create</button>
                </div>
            </div>
        </div>

        <!-- Rename Dialog -->
        <div
            v-if="showRenameDialog"
            class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            @click.self="showRenameDialog = false"
        >
            <div class="bg-white dark:bg-zinc-900 rounded-2xl p-6 w-full max-w-md mx-4 shadow-xl space-y-4">
                <div class="text-lg font-semibold text-gray-900 dark:text-white">Rename Server</div>
                <div>
                    <label class="glass-label">New Name</label>
                    <input
                        v-model="renameNodeName"
                        type="text"
                        :placeholder="selectedNode ? selectedNode.name : ''"
                        class="input-field"
                        @keyup.enter="renameNode"
                    />
                </div>
                <div class="flex justify-end gap-2">
                    <button class="secondary-chip !py-1.5 !px-4 !text-sm" @click="showRenameDialog = false">
                        Cancel
                    </button>
                    <button class="primary-chip !py-1.5 !px-4 !text-sm" @click="renameNode">Rename</button>
                </div>
            </div>
        </div>

        <!-- Status message -->
        <div
            v-if="statusMessage"
            class="fixed bottom-4 right-4 z-50 p-3 rounded-lg shadow-lg text-sm"
            :class="
                statusSuccess
                    ? 'bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-200'
                    : 'bg-red-100 dark:bg-red-900/40 text-red-800 dark:text-red-200'
            "
        >
            {{ statusMessage }}
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import DialogUtils from "../../js/DialogUtils";

export default {
    name: "PageNodesPage",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            nodes: [],
            loading: true,
            selectedNode: null,
            detailTab: "pages",
            showCreateDialog: false,
            showRenameDialog: false,
            createNodeName: "",
            renameNodeName: "",
            newPageName: "",
            editingPage: null,
            editingPageContent: "",
            statusMessage: "",
            statusSuccess: true,
            statusTimeout: null,
        };
    },
    async mounted() {
        await this.loadNodes();
    },
    methods: {
        async loadNodes() {
            this.loading = true;
            try {
                const response = await window.axios.get("/api/v1/page-nodes");
                this.nodes = response.data;
                if (this.selectedNode) {
                    const updated = this.nodes.find((n) => n.node_id === this.selectedNode.node_id);
                    if (updated) {
                        this.selectedNode = updated;
                    } else {
                        this.selectedNode = null;
                    }
                }
            } catch (_) {
                this.showStatus("Failed to load nodes", false);
            } finally {
                this.loading = false;
            }
        },
        selectNode(node) {
            this.selectedNode = node;
            this.detailTab = "pages";
            this.editingPage = null;
        },
        async createNode() {
            if (!this.createNodeName.trim()) return;
            try {
                await window.axios.post("/api/v1/page-nodes", { name: this.createNodeName.trim() });
                this.createNodeName = "";
                this.showCreateDialog = false;
                this.showStatus("Server created", true);
                await this.loadNodes();
            } catch (e) {
                this.showStatus(e.response?.data?.message || "Failed to create server", false);
            }
        },
        async deleteNode(nodeId) {
            if (!(await DialogUtils.confirm("Delete this mesh server and all its content?"))) return;
            try {
                await window.axios.delete(`/api/v1/page-nodes/${nodeId}`);
                if (this.selectedNode && this.selectedNode.node_id === nodeId) {
                    this.selectedNode = null;
                }
                this.showStatus("Server deleted", true);
                await this.loadNodes();
            } catch (_) {
                this.showStatus("Failed to delete server", false);
            }
        },
        async startNode(nodeId) {
            try {
                const response = await window.axios.post(`/api/v1/page-nodes/${nodeId}/start`);
                this.showStatus(`Server started: ${response.data.destination_hash}`, true);
                await this.loadNodes();
            } catch (e) {
                this.showStatus(e.response?.data?.message || "Failed to start server", false);
            }
        },
        async stopNode(nodeId) {
            try {
                await window.axios.post(`/api/v1/page-nodes/${nodeId}/stop`);
                this.showStatus("Server stopped", true);
                await this.loadNodes();
            } catch (_) {
                this.showStatus("Failed to stop server", false);
            }
        },
        async announceNode(nodeId) {
            try {
                await window.axios.post(`/api/v1/page-nodes/${nodeId}/announce`);
                this.showStatus("Announced on mesh", true);
            } catch (_) {
                this.showStatus("Failed to announce", false);
            }
        },
        async renameNode() {
            if (!this.renameNodeName.trim() || !this.selectedNode) return;
            try {
                await window.axios.put(`/api/v1/page-nodes/${this.selectedNode.node_id}/rename`, {
                    name: this.renameNodeName.trim(),
                });
                this.renameNodeName = "";
                this.showRenameDialog = false;
                this.showStatus("Server renamed", true);
                await this.loadNodes();
            } catch (_) {
                this.showStatus("Failed to rename server", false);
            }
        },
        async addPage() {
            if (!this.newPageName.trim() || !this.selectedNode) return;
            try {
                await window.axios.post(`/api/v1/page-nodes/${this.selectedNode.node_id}/pages`, {
                    name: this.newPageName.trim(),
                    content: "",
                });
                this.newPageName = "";
                this.showStatus("Page created", true);
                await this.loadNodes();
            } catch (_) {
                this.showStatus("Failed to create page", false);
            }
        },
        async editPage(pageName) {
            try {
                const response = await window.axios.get(
                    `/api/v1/page-nodes/${this.selectedNode.node_id}/pages/${encodeURIComponent(pageName)}`
                );
                this.editingPage = pageName;
                this.editingPageContent = response.data.content;
            } catch (_) {
                this.showStatus("Failed to load page", false);
            }
        },
        async savePage() {
            if (!this.editingPage || !this.selectedNode) return;
            try {
                await window.axios.post(`/api/v1/page-nodes/${this.selectedNode.node_id}/pages`, {
                    name: this.editingPage,
                    content: this.editingPageContent,
                });
                this.editingPage = null;
                this.editingPageContent = "";
                this.showStatus("Page saved", true);
                await this.loadNodes();
            } catch (_) {
                this.showStatus("Failed to save page", false);
            }
        },
        async deletePage(pageName) {
            if (!(await DialogUtils.confirm(`Delete page "${pageName}"?`))) return;
            try {
                await window.axios.delete(
                    `/api/v1/page-nodes/${this.selectedNode.node_id}/pages/${encodeURIComponent(pageName)}`
                );
                if (this.editingPage === pageName) {
                    this.editingPage = null;
                }
                this.showStatus("Page deleted", true);
                await this.loadNodes();
            } catch (_) {
                this.showStatus("Failed to delete page", false);
            }
        },
        async uploadFile(event) {
            const file = event.target.files[0];
            if (!file || !this.selectedNode) return;
            const formData = new FormData();
            formData.append("file", file);
            try {
                await window.axios.post(`/api/v1/page-nodes/${this.selectedNode.node_id}/files`, formData, {
                    headers: { "Content-Type": "multipart/form-data" },
                });
                this.showStatus("File uploaded", true);
                await this.loadNodes();
            } catch (_) {
                this.showStatus("Failed to upload file", false);
            }
            event.target.value = "";
        },
        async deleteFile(fileName) {
            if (!(await DialogUtils.confirm(`Delete file "${fileName}"?`))) return;
            try {
                await window.axios.delete(
                    `/api/v1/page-nodes/${this.selectedNode.node_id}/files/${encodeURIComponent(fileName)}`
                );
                this.showStatus("File deleted", true);
                await this.loadNodes();
            } catch (_) {
                this.showStatus("Failed to delete file", false);
            }
        },
        viewNode(node) {
            if (node.destination_hash) {
                this.$router.push({
                    name: "nomadnetwork",
                    params: { destinationHash: node.destination_hash },
                });
            }
        },
        formatFileSize(bytes) {
            if (bytes < 1024) return bytes + " B";
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
            return (bytes / (1024 * 1024)).toFixed(1) + " MB";
        },
        showStatus(message, success) {
            this.statusMessage = message;
            this.statusSuccess = success;
            if (this.statusTimeout) clearTimeout(this.statusTimeout);
            this.statusTimeout = setTimeout(() => {
                this.statusMessage = "";
            }, 3000);
        },
    },
};
</script>
