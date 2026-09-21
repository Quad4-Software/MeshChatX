// SPDX-License-Identifier: 0BSD

export interface IdentityScopeOptions {
    getIdentityKey?: () => string;
}

export interface IdentityScope {
    identityKey: { value: string };
    beginIdentity(explicitHash?: string): string;
    keyForWrite(explicitKey?: string): string;
}

/**
 * Shared identity scope for per-identity localStorage state.
 *
 * The leak this prevents: a deferred save (room switch, route leave,
 * unmount, identity switch) that resolves the live identity writes one
 * identity's data into another's bucket. The scope makes the safe path
 * the default:
 *  - beginIdentity captures the identity at load time. An explicit hash
 *    (for example the identity_switched payload) wins over live config,
 *    which can lag the event.
 *  - keyForWrite prefers the captured key, so deferred saves land in the
 *    bucket the state was loaded from. Live config is only a fallback
 *    for state that was never loaded, where nothing can leak.
 *
 * Usage: call beginIdentity wherever identity-scoped state is loaded or
 * an identity_switched event arrives, and resolve every storage write
 * through keyForWrite.
 */
export function useIdentityScope(options: IdentityScopeOptions = {}): IdentityScope {
    const getIdentityKey = options.getIdentityKey || (() => "_");
    const identityKey = { value: "" };

    function normalizeIdentityKey(value: unknown): string {
        return typeof value === "string" && value ? value : "_";
    }

    function beginIdentity(explicitHash?: string): string {
        identityKey.value = normalizeIdentityKey(explicitHash || getIdentityKey());
        return identityKey.value;
    }

    function keyForWrite(explicitKey?: string): string {
        return normalizeIdentityKey(explicitKey || identityKey.value || getIdentityKey());
    }

    return { identityKey, beginIdentity, keyForWrite };
}
