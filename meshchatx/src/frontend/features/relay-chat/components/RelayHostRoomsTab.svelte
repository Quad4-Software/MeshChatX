<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import DialogUtils from "../../../js/DialogUtils.js";
    import ToastUtils from "../../../js/ToastUtils.js";
    import { t } from "../../../js/i18n.js";

    interface Props {
        hubId: string;
        roomsActivity?: { name: string; member_count?: number; topic?: string; has_key?: boolean }[];
        onRefresh?: () => void;
        onFetchActivity?: () => void;
    }

    let { hubId, roomsActivity = [], onRefresh, onFetchActivity }: Props = $props();

    let roomsSearch = $state("");
    let showAddRoomForm = $state(false);
    let creatingRoom = $state(false);
    let newRoom = $state({ name: "", topic: "", key: "" });

    const filteredRooms = $derived.by(() => {
        if (!roomsSearch.trim()) return roomsActivity;
        const clean = roomsSearch.toLowerCase();
        return roomsActivity.filter(
            (r) => r.name.toLowerCase().includes(clean) || (r.topic || "").toLowerCase().includes(clean)
        );
    });

    async function createRoom() {
        if (!hubId || !newRoom.name.trim()) return;
        creatingRoom = true;
        const api = (window as any).api;
        if (!api) return;
        try {
            await api.post(`/api/v1/rrc/servers/${hubId}/rooms`, {
                name: newRoom.name.trim(),
                topic: newRoom.topic.trim() || null,
                key: newRoom.key || null,
            });
            ToastUtils.success(t("relay_chat.host_room_created"));
            newRoom = { name: "", topic: "", key: "" };
            showAddRoomForm = false;
            onFetchActivity?.();
            onRefresh?.();
        } catch (e: any) {
            ToastUtils.error(e.response?.data?.message || t("relay_chat.action_failed"));
        } finally {
            creatingRoom = false;
        }
    }

    async function deleteRoom(roomName: string) {
        if (!hubId) return;
        if (await DialogUtils.confirm(t("relay_chat.host_delete_room_confirm"))) {
            const api = (window as any).api;
            if (!api) return;
            try {
                await api.delete(`/api/v1/rrc/servers/${hubId}/rooms/${encodeURIComponent(roomName)}`);
                ToastUtils.success(t("relay_chat.host_room_deleted"));
                onFetchActivity?.();
                onRefresh?.();
            } catch (e: any) {
                ToastUtils.error(e.response?.data?.message || t("relay_chat.action_failed"));
            }
        }
    }
</script>

<div class="flex flex-1 min-h-0 overflow-hidden">
    <div class="flex flex-col w-full sm:w-80 border-r border-sem-border bg-sem-surface p-3 space-y-3 overflow-y-auto">
        <div class="relative">
            <MaterialDesignIcon
                iconName="magnify"
                class="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-sem-fg-muted"
            />
            <input
                type="search"
                bind:value={roomsSearch}
                placeholder={t("relay_chat.host_rooms_search")}
                class="w-full pl-8 pr-2 py-1.5 text-xs bg-sem-canvas border border-sem-border rounded-lg text-sem-fg"
            />
        </div>

        {#if !showAddRoomForm}
            <button
                type="button"
                class="flex w-full items-center gap-2 rounded-xl border-2 border-dashed border-sem-border px-3 py-2.5 text-left text-xs font-medium text-sem-fg-muted hover:border-sem-accent hover:text-sem-accent transition-colors cursor-pointer"
                onclick={() => {
                    showAddRoomForm = true;
                }}
            >
                <MaterialDesignIcon iconName="plus-circle-outline" class="size-4" />
                <span>{t("relay_chat.host_add_room")}</span>
            </button>
        {:else}
            <form
                class="space-y-2 rounded-xl border border-sem-border bg-sem-canvas p-3"
                onsubmit={(e) => {
                    e.preventDefault();
                    createRoom();
                }}
            >
                <input
                    type="text"
                    bind:value={newRoom.name}
                    placeholder={t("relay_chat.host_room_name")}
                    class="w-full px-2 py-1 text-xs bg-sem-surface border border-sem-border rounded text-sem-fg"
                />
                <input
                    type="text"
                    bind:value={newRoom.topic}
                    placeholder={t("relay_chat.host_room_topic")}
                    class="w-full px-2 py-1 text-xs bg-sem-surface border border-sem-border rounded text-sem-fg"
                />
                <input
                    type="password"
                    bind:value={newRoom.key}
                    placeholder={t("relay_chat.host_room_key_placeholder")}
                    class="w-full px-2 py-1 text-xs bg-sem-surface border border-sem-border rounded text-sem-fg"
                />
                <div class="flex gap-2 pt-1">
                    <button
                        type="submit"
                        class="flex-1 py-1 px-2 rounded bg-sem-action-primary text-xs font-semibold text-white cursor-pointer"
                        disabled={creatingRoom}
                    >
                        {t("relay_chat.host_add_room")}
                    </button>
                    <button
                        type="button"
                        class="py-1 px-2 rounded border border-sem-border text-xs text-sem-fg cursor-pointer"
                        onclick={() => {
                            showAddRoomForm = false;
                        }}
                    >
                        {t("common.cancel")}
                    </button>
                </div>
            </form>
        {/if}

        <div class="space-y-1">
            {#each filteredRooms as room (room.name)}
                <div
                    class="flex items-center justify-between p-2 rounded-lg border border-sem-border hover:bg-sem-surface-muted text-xs"
                >
                    <div class="min-w-0 flex-1 mr-2">
                        <div class="flex items-center gap-1 font-semibold">
                            <span>#{room.name}</span>
                            {#if room.has_key}
                                <MaterialDesignIcon iconName="lock" class="size-3 text-amber-500" />
                            {/if}
                        </div>
                        {#if room.topic}
                            <div class="text-[11px] text-sem-fg-muted truncate">{room.topic}</div>
                        {/if}
                    </div>
                    <button
                        type="button"
                        class="p-1 rounded text-sem-fg-muted hover:text-red-500 cursor-pointer"
                        title={t("common.delete")}
                        onclick={() => deleteRoom(room.name)}
                    >
                        <MaterialDesignIcon iconName="trash-can-outline" class="size-4" />
                    </button>
                </div>
            {/each}
        </div>
    </div>

    <div class="flex-1 p-6 flex items-center justify-center text-center text-sm text-sem-fg-muted">
        {t("relay_chat.host_rooms_management_hint")}
    </div>
</div>
