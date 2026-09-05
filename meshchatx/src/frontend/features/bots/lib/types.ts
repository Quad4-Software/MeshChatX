// SPDX-License-Identifier: 0BSD

export interface BotLxmfConfig {
    propagation_mode?: string;
    propagation_node?: string;
    propagation_fallback_enabled?: boolean | null;
    direct_delivery_retries?: number | null;
    opportunistic_sending?: boolean | null;
    announce_interval_seconds?: number | null;
    stamp_cost?: number | null;
}

export interface LxmfConfigDraft {
    propagation_mode: string;
    propagation_node: string;
    propagation_fallback_enabled: string;
    direct_delivery_retries: string;
    opportunistic_sending: string;
    announce_interval_seconds: string;
    stamp_cost: string;
}

export type LxmfConfigPatch = {
    propagation_mode?: string;
    propagation_node?: string | null;
    propagation_fallback_enabled?: boolean | null;
    direct_delivery_retries?: number | null;
    opportunistic_sending?: boolean | null;
    announce_interval_seconds?: number | null;
    stamp_cost?: number | null;
};

export interface BotRecord {
    id: string;
    name: string;
    address?: string;
    full_address?: string;
    lxmf_address?: string;
    running: boolean;
    template?: string;
    template_id?: string;
    last_announce_at?: string | null;
    last_error?: string | null;
    lxmf_config?: BotLxmfConfig | null;
    effective_lxmf_config?: Record<string, unknown> | null;
}

export interface BotTemplate {
    id: string;
    name: string;
    description: string;
}
