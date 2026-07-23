// SPDX-License-Identifier: 0BSD

import Utils from "../../../js/Utils.js";

export function lxmfDeliveryDestinationHexFromContact(contact) {
    if (!contact) return "";
    const order = [contact.remote_destination_hash, contact.lxmf_address, contact.remote_identity_hash];
    for (const c of order) {
        const h = Utils.normalizeMeshchatHashHex(c);
        if (h) {
            return h;
        }
    }
    return "";
}

export function lxmfContactResolvedIcon(contact, conversations = []) {
    const empty = { iconName: "", foreground: "", background: "" };
    if (!contact) {
        return empty;
    }
    const ri = contact.remote_icon;
    if (ri?.icon_name) {
        return {
            iconName: ri.icon_name,
            foreground: ri.foreground_colour || "",
            background: ri.background_colour || "",
        };
    }
    const dest = lxmfDeliveryDestinationHexFromContact(contact);
    if (!dest) {
        return empty;
    }
    const conv =
        (conversations || []).find((c) => Utils.normalizeMeshchatHashHex(c.destination_hash || "") === dest) || null;
    const lu = conv?.lxmf_user_icon;
    if (lu?.icon_name) {
        return {
            iconName: lu.icon_name,
            foreground: lu.foreground_colour || "",
            background: lu.background_colour || "",
        };
    }
    return empty;
}
