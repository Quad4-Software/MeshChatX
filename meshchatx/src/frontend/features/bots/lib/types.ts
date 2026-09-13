// SPDX-License-Identifier: 0BSD

export type { BotLxmfConfig, LxmfConfigDraft, LxmfConfigPatch } from "./botLxmfConfigForm.js";

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
