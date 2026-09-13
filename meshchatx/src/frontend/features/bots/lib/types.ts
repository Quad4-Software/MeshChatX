// SPDX-License-Identifier: 0BSD

import type { BotLxmfConfig, LxmfConfigDraft, LxmfConfigPatch } from "./botLxmfConfigForm.js";

export type { BotLxmfConfig, LxmfConfigDraft, LxmfConfigPatch };

export interface BotIconDraft {
    icon_name: string;
    fg_color: string;
    bg_color: string;
}

export interface BotRrcConfig {
    hub?: string;
    rooms?: string[];
    nick?: string | null;
    mention_only?: boolean;
    prefix?: string;
    rate_seconds?: number;
}

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
    icon?: BotIconDraft | null;
    custom?: unknown;
    rrc?: BotRrcConfig | null;
}

export interface BotTemplate {
    id: string;
    name: string;
    description: string;
    default_icon?: string;
}
