<template>
    <DropDownMenu>
        <template #button>
            <IconButton>
                <MaterialDesignIcon icon-name="dots-vertical" class="size-5" />
            </IconButton>
        </template>
        <template #items>
            <!-- call button -->
            <DropDownMenuItem @click="onStartCall">
                <MaterialDesignIcon icon-name="phone" class="w-4 h-4" />
                <span>Start a Call</span>
            </DropDownMenuItem>

            <!-- ping button -->
            <DropDownMenuItem @click="onPingDestination">
                <MaterialDesignIcon icon-name="flash" class="size-5" />
                <span>Ping Destination</span>
            </DropDownMenuItem>

            <!-- set custom display name button -->
            <DropDownMenuItem @click="onSetCustomDisplayName">
                <MaterialDesignIcon icon-name="account-edit" class="size-5" />
                <span>Set Custom Display Name</span>
            </DropDownMenuItem>

            <!-- block/unblock button -->
            <div class="border-t">
                <DropDownMenuItem v-if="!isBlocked" @click="onBlockDestination">
                    <MaterialDesignIcon icon-name="block-helper" class="size-5 text-red-500" />
                    <span class="text-red-500">Block User</span>
                </DropDownMenuItem>
                <DropDownMenuItem v-else @click="onUnblockDestination">
                    <MaterialDesignIcon icon-name="check-circle" class="size-5 text-green-500" />
                    <span class="text-green-500">Unblock User</span>
                </DropDownMenuItem>
            </div>

            <!-- delete message history button -->
            <div class="border-t">
                <DropDownMenuItem @click="onDeleteMessageHistory">
                    <MaterialDesignIcon icon-name="delete" class="size-5 text-red-500" />
                    <span class="text-red-500">Delete Message History</span>
                </DropDownMenuItem>
            </div>
        </template>
    </DropDownMenu>
</template>

<script>
import DropDownMenu from "../DropDownMenu.vue";
import DropDownMenuItem from "../DropDownMenuItem.vue";
import IconButton from "../IconButton.vue";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import DialogUtils from "../../js/DialogUtils";

export default {
    name: "ConversationDropDownMenu",
    components: {
        IconButton,
        DropDownMenuItem,
        DropDownMenu,
        MaterialDesignIcon,
    },
    props: {
        peer: {
            type: Object,
            required: true,
        },
    },
    emits: ["conversation-deleted", "set-custom-display-name", "block-status-changed"],
    data() {
        return {
            isBlocked: false,
            blockedDestinations: [],
        };
    },
    watch: {
        peer: {
            handler() {
                this.checkIfBlocked();
            },
            immediate: true,
        },
    },
    async mounted() {
        await this.loadBlockedDestinations();
    },
    methods: {
        async loadBlockedDestinations() {
            try {
                const response = await window.axios.get("/api/v1/blocked-destinations");
                this.blockedDestinations = response.data.blocked_destinations || [];
                this.checkIfBlocked();
            } catch (e) {
                console.log(e);
            }
        },
        checkIfBlocked() {
            if (!this.peer) {
                this.isBlocked = false;
                return;
            }
            this.isBlocked = this.blockedDestinations.some((b) => b.destination_hash === this.peer.destination_hash);
        },
        async onBlockDestination() {
            if (
                !(await DialogUtils.confirm(
                    "Are you sure you want to block this user? They will not be able to send you messages or establish links."
                ))
            ) {
                return;
            }

            try {
                await window.axios.post("/api/v1/blocked-destinations", {
                    destination_hash: this.peer.destination_hash,
                });
                await this.loadBlockedDestinations();
                DialogUtils.alert("User blocked successfully");
                this.$emit("block-status-changed");
            } catch (e) {
                DialogUtils.alert("Failed to block user");
                console.log(e);
            }
        },
        async onUnblockDestination() {
            try {
                await window.axios.delete(`/api/v1/blocked-destinations/${this.peer.destination_hash}`);
                await this.loadBlockedDestinations();
                DialogUtils.alert("User unblocked successfully");
                this.$emit("block-status-changed");
            } catch (e) {
                DialogUtils.alert("Failed to unblock user");
                console.log(e);
            }
        },
        async onDeleteMessageHistory() {
            // ask user to confirm deleting conversation history
            if (
                !(await DialogUtils.confirm(
                    "Are you sure you want to delete all messages in this conversation? This can not be undone!"
                ))
            ) {
                return;
            }

            // delete all lxmf messages from "us to destination" and from "destination to us"
            try {
                await window.axios.delete(`/api/v1/lxmf-messages/conversation/${this.peer.destination_hash}`);
            } catch (e) {
                DialogUtils.alert("failed to delete conversation");
                console.log(e);
            }

            // fire callback
            this.$emit("conversation-deleted");
        },
        async onSetCustomDisplayName() {
            this.$emit("set-custom-display-name");
        },
        async onStartCall() {
            try {
                await window.axios.get(`/api/v1/telephone/call/${this.peer.destination_hash}`);
            } catch (e) {
                const message = e.response?.data?.message ?? "Failed to start call";
                DialogUtils.alert(message);
            }
        },
        async onPingDestination() {
            try {
                // ping destination
                const response = await window.axios.get(`/api/v1/ping/${this.peer.destination_hash}/lxmf.delivery`, {
                    params: {
                        timeout: 30,
                    },
                });

                const pingResult = response.data.ping_result;
                const rttMilliseconds = (pingResult.rtt * 1000).toFixed(3);
                const rttDurationString = `${rttMilliseconds} ms`;

                const info = [
                    `Valid reply from ${this.peer.destination_hash}`,
                    `Duration: ${rttDurationString}`,
                    `Hops There: ${pingResult.hops_there}`,
                    `Hops Back: ${pingResult.hops_back}`,
                ];

                // add signal quality if available
                if (pingResult.quality != null) {
                    info.push(`Signal Quality: ${pingResult.quality}%`);
                }

                // add rssi if available
                if (pingResult.rssi != null) {
                    info.push(`RSSI: ${pingResult.rssi}dBm`);
                }

                // add snr if available
                if (pingResult.snr != null) {
                    info.push(`SNR: ${pingResult.snr}dB`);
                }

                // show result
                DialogUtils.alert(info.join("\n"));
            } catch (e) {
                console.log(e);
                const message = e.response?.data?.message ?? "Ping failed. Try again later";
                DialogUtils.alert(message);
            }
        },
    },
};
</script>
