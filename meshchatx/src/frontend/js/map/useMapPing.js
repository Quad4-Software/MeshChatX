// @ts-check

import { computed, ref } from "vue";

import ToastUtils from "../ToastUtils.js";
import { apiPath } from "../constants.js";
import { buildMeshchatMapUri } from "../mapLinkUtils.js";

/**
 * Map ping modal state for MapPage: target coordinates, destination hash
 * selection, the summary label, and the send action.
 *
 * options.t translates i18n keys (the host passes its $t) and
 * options.getLayers returns the share layers tag (the host passes
 * layersTagForShare) so the composable stays free of instance-only APIs.
 */
export function useMapPing(options = {}) {
    const { t = (key) => key, getLayers = () => "" } = options;

    const showMapPingModal = ref(false);
    const pingDestinationHash = ref("");
    const mapPingLat = ref(0);
    const mapPingLon = ref(0);
    const mapPingZoom = ref(10);

    const mapPingSummary = computed(() => {
        return `${mapPingLat.value.toFixed(6)}, ${mapPingLon.value.toFixed(6)} @ z${Math.round(mapPingZoom.value)}`;
    });

    function openPingModalAt(lat, lon, zoom) {
        mapPingLat.value = lat;
        mapPingLon.value = lon;
        mapPingZoom.value = zoom;
        pingDestinationHash.value = "";
        showMapPingModal.value = true;
    }

    async function sendMapPing() {
        const hash = (pingDestinationHash.value || "").trim();
        if (!hash || hash.length !== 32) {
            ToastUtils.error(t("map.ping_invalid_destination"));
            return;
        }
        const layers = getLayers();
        const uri = buildMeshchatMapUri({
            lat: mapPingLat.value,
            lon: mapPingLon.value,
            zoom: mapPingZoom.value,
            layers,
            label: "Ping",
        });
        const content = `${t("map.ping_message_prefix")} ${uri}`;
        try {
            await window.api.post(apiPath("/lxmf-messages/send"), {
                lxmf_message: {
                    destination_hash: hash,
                    content,
                },
            });
            ToastUtils.success(t("map.ping_sent"));
            showMapPingModal.value = false;
        } catch (e) {
            console.error(e);
            ToastUtils.error(t("map.ping_failed"));
        }
    }

    return {
        showMapPingModal,
        pingDestinationHash,
        mapPingLat,
        mapPingLon,
        mapPingZoom,
        mapPingSummary,
        openPingModalAt,
        sendMapPing,
    };
}
