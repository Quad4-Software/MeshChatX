// SPDX-License-Identifier: 0BSD

export type LxmaUriParts = {
    destinationHash: string;
    publicKeyHex: string;
    normalizedUri: string;
};

export type IdentityConfig = {
    lxmf_address_hash?: string;
    identity_public_key?: string;
};

export type ContactUriFields = {
    lxmf_address?: string;
    remote_identity_hash?: string;
};

export function parseLxmaUri(input: string): LxmaUriParts | null {
    const normalized = input.trim();
    const match = normalized.match(/^lxma:\/\/([0-9a-f]{32}):([0-9a-f]{64}|[0-9a-f]{128})$/i);
    if (!match) {
        return null;
    }
    return {
        destinationHash: match[1].toLowerCase(),
        publicKeyHex: match[2].toLowerCase(),
        normalizedUri: `lxma://${match[1].toLowerCase()}:${match[2].toLowerCase()}`,
    };
}

export function extractDestinationHash(input: string): string | null {
    const raw = input.trim().toLowerCase();
    if (/^[0-9a-f]{32}$/.test(raw)) {
        return raw;
    }
    const lxmfMatch = raw.match(/^lxmf:\/\/([0-9a-f]{32})$/);
    if (lxmfMatch) {
        return lxmfMatch[1];
    }
    const lxmMatch = raw.match(/^lxm:\/\/([0-9a-f]{32})$/);
    if (lxmMatch) {
        return lxmMatch[1];
    }
    return null;
}

export function buildMyIdentityUri(config: IdentityConfig | null | undefined): string | null {
    if (!config?.lxmf_address_hash) {
        return null;
    }
    if (config?.identity_public_key) {
        return `lxma://${config.lxmf_address_hash}:${config.identity_public_key}`;
    }
    return `lxmf://${config.lxmf_address_hash}`;
}

/**
 * Decode announce identity_public_key (base64) to hex for lxma URIs.
 */
export function publicKeyFromAnnounce(publicKeyBase64: string | null | undefined): string | null {
    if (!publicKeyBase64) {
        return null;
    }
    try {
        const binary = atob(publicKeyBase64);
        const publicKeyHex = Array.from(binary)
            .map((c) => c.charCodeAt(0).toString(16).padStart(2, "0"))
            .join("");
        if (publicKeyHex.length !== 64 && publicKeyHex.length !== 128) {
            return null;
        }
        return publicKeyHex;
    } catch {
        return null;
    }
}

export function buildContactUri(contact: ContactUriFields, publicKeyHex: string | null): string | null {
    const destinationHash = (contact?.lxmf_address || contact?.remote_identity_hash || "").toLowerCase();
    if (!/^[0-9a-f]{32}$/.test(destinationHash)) {
        return null;
    }
    if (publicKeyHex) {
        return `lxma://${destinationHash}:${publicKeyHex}`;
    }
    return `lxmf://${destinationHash}`;
}
