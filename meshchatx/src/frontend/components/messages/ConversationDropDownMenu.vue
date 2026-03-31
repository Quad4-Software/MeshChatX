<template>
    <DropDownMenu>
        <template #button>
            <IconButton>
                <MaterialDesignIcon icon-name="dots-vertical" class="size-7" />
            </IconButton>
        </template>
        <template #items>
            <!-- popout button -->
            <DropDownMenuItem @click="$emit('popout')">
                <MaterialDesignIcon icon-name="open-in-new" class="size-5" />
                <span>Popout Chat</span>
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
                    <MaterialDesignIcon icon-name="gavel" class="size-5 text-red-500" />
                    <span class="text-red-500">Banish User</span>
                </DropDownMenuItem>
                <DropDownMenuItem v-else @click="onUnblockDestination">
                    <MaterialDesignIcon icon-name="check-circle" class="size-5 text-green-500" />
                    <span class="text-green-500">Lift Banishment</span>
                </DropDownMenuItem>
            </div>

            <!-- delete message history button -->
            <div class="border-t">
                <DropDownMenuItem @click="onDeleteMessageHistory">
                    <MaterialDesignIcon icon-name="delete" class="size-5 text-red-500" />
                    <span class="text-red-500">Delete Message History</span>
                </DropDownMenuItem>
            </div>

            <!-- telemetry trust toggle -->
            <div v-if="GlobalState.config.telemetry_enabled" class="border-t">
                <DropDownMenuItem @click="onToggleTelemetryTrust">
                    <MaterialDesignIcon
                        :icon-name="contact?.is_telemetry_trusted ? 'shield-check' : 'shield-outline'"
                        :class="contact?.is_telemetry_trusted ? 'text-blue-500' : 'text-gray-500'"
                        class="size-5"
                    />
                    <span>{{
                        contact?.is_telemetry_trusted
                            ? $t("app.telemetry_trust_revoke")
                            : $t("app.telemetry_trust_grant")
                    }}</span>
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
import GlobalState from "../../js/GlobalState";
import GlobalEmitter from "../../js/GlobalEmitter";

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
    emits: [
        "conversation-deleted",
        "set-custom-display-name",
        "block-status-changed",
        "popout",
        "view-telemetry-history",
    ],
    data() {
        return {
            contact: null,
        };
    },
    computed: {
        isBlocked() {
            if (!this.peer) {
                return false;
            }
            return GlobalState.blockedDestinations.some((b) => b.destination_hash === this.peer.destination_hash);
        },
    },
    watch: {
        peer: {
            immediate: true,
            handler() {
                this.fetchContact();
            },
        },
    },
    mounted() {
        GlobalEmitter.on("contact-updated", this.onContactUpdated);
    },
    unmounted() {
        GlobalEmitter.off("contact-updated", this.onContactUpdated);
    },
    methods: {
        onContactUpdated(data) {
            if (this.peer?.destination_hash === data.remote_identity_hash) {
                this.fetchContact();
            }
        },
        async fetchContact() {
            if (!this.peer || !this.peer.destination_hash) return;
            try {
                const response = await window.api.get(`/api/v1/telephone/contacts/check/${this.peer.destination_hash}`);
                if (response.data.is_contact) {
                    this.contact = response.data.contact;
                } else {
                    this.contact = null;
                }
            } catch (e) {
                console.error("Failed to fetch contact", e);
            }
        },
        async onToggleTelemetryTrust() {
            const newStatus = !this.contact?.is_telemetry_trusted;
            try {
                if (!this.contact) {
                    // create contact first
                    await window.api.post("/api/v1/telephone/contacts", {
                        name: this.peer.display_name,
                        remote_identity_hash: this.peer.destination_hash,
                        is_telemetry_trusted: true,
                    });
                    await this.fetchContact();
                } else {
                    await window.api.patch(`/api/v1/telephone/contacts/${this.contact.id}`, {
                        is_telemetry_trusted: newStatus,
                    });
                    this.contact.is_telemetry_trusted = newStatus;
                }
                GlobalEmitter.emit("contact-updated", {
                    remote_identity_hash: this.peer.destination_hash,
                    is_telemetry_trusted: newStatus,
                });
                DialogUtils.alert(
                    newStatus
                        ? this.$t("app.telemetry_trust_granted_alert")
                        : this.$t("app.telemetry_trust_revoked_alert")
                );
            } catch (e) {
                DialogUtils.alert(this.$t("app.telemetry_trust_failed"));
                console.error(e);
            }
        },
        async onBlockDestination() {
            if (
                !(await DialogUtils.confirm(
                    "Are you sure you want to banish this user? They will not be able to send you messages or establish links."
                ))
            ) {
                return;
            }

            try {
                await window.api.post("/api/v1/blocked-destinations", {
                    destination_hash: this.peer.destination_hash,
                });
                GlobalEmitter.emit("block-status-changed");
                DialogUtils.alert(this.$t("messages.user_banished"));
                this.$emit("block-status-changed");
            } catch (e) {
                DialogUtils.alert(this.$t("messages.failed_banish_user"));
                console.log(e);
            }
        },
        async onUnblockDestination() {
            try {
                await window.api.delete(`/api/v1/blocked-destinations/${this.peer.destination_hash}`);
                GlobalEmitter.emit("block-status-changed");
                DialogUtils.alert(this.$t("banishment.banishment_lifted"));
                this.$emit("block-status-changed");
            } catch (e) {
                DialogUtils.alert(this.$t("banishment.failed_lift_banishment"));
                console.log(e);
            }
        },
        async onDeleteMessageHistory() {
            // ask user to confirm deleting conversation history
            if (!(await DialogUtils.confirm(this.$t("messages.delete_history_confirm")))) {
                return;
            }

            // delete all lxmf messages from "us to destination" and from "destination to us"
            try {
                await window.api.delete(`/api/v1/lxmf-messages/conversation/${this.peer.destination_hash}`);
            } catch (e) {
                DialogUtils.alert(this.$t("messages.failed_delete_history"));
                console.log(e);
            }

            // fire callback
            this.$emit("conversation-deleted");
        },
        async onSetCustomDisplayName() {
            this.$emit("set-custom-display-name");
        },
        async onPingDestination() {
            if (!this.peer || !this.peer.destination_hash) {
                DialogUtils.alert(this.$t("messages.invalid_destination_hash"));
                return;
            }

            const destinationHash = this.peer.destination_hash;
            if (destinationHash.length !== 32 || !/^[0-9a-fA-F]+$/.test(destinationHash)) {
                DialogUtils.alert(this.$t("messages.invalid_destination_hash_format"));
                return;
            }

            try {
                // ping destination
                const response = await window.api.get(`/api/v1/ping/${destinationHash}/lxmf.delivery`, {
                    params: {
                        timeout: 30,
                    },
                });

                const pingResult = response.data.ping_result;
                const rttMilliseconds = (pingResult.rtt * 1000).toFixed(3);
                const rttDurationString = `${rttMilliseconds} ms`;

                const info = [
                    this.$t("messages.ping_reply_from", { hash: destinationHash }),
                    this.$t("messages.duration", { duration: rttDurationString }),
                    this.$t("messages.hops_there", { count: pingResult.hops_there }),
                    this.$t("messages.hops_back", { count: pingResult.hops_back }),
                ];

                // add signal quality if available
                if (pingResult.quality != null) {
                    info.push(this.$t("messages.signal_quality", { quality: pingResult.quality }));
                }

                // add rssi if available
                if (pingResult.rssi != null) {
                    info.push(this.$t("messages.rssi_val", { rssi: pingResult.rssi }));
                }

                // add snr if available
                if (pingResult.snr != null) {
                    info.push(this.$t("messages.snr_val", { snr: pingResult.snr }));
                }

                // show result
                DialogUtils.alert(info.join("\n"));
            } catch (e) {
                console.log(e);
                const message = e.response?.data?.message ?? this.$t("messages.ping_failed");
                DialogUtils.alert(message);
            }
        },
    },
};
</script>
