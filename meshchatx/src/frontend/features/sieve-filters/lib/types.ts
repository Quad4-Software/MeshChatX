// SPDX-License-Identifier: 0BSD

export type SieveRuleScope = "everyone" | "contacts" | "non_contacts";

export type SieveRuleAction = "hide" | "ignore" | "folder" | "banish" | "block";

export type SieveMatchMode = "substring" | "regex";

export interface SieveRule {
    id: string;
    enabled: boolean;
    scope: SieveRuleScope;
    terms: string[];
    action: SieveRuleAction;
    folder_id: number | null;
    match_peer_fields: boolean;
    match_message: boolean;
    match_mode: SieveMatchMode;
}

export interface SieveFolder {
    id: number;
    name: string;
}

export interface SieveFlowLabels {
    sourceNode?: string;
    sourceHint?: string;
    rulePrefix?: string;
    hide?: string;
    ignore?: string;
    banish?: string;
    folder?: string;
    noRules?: string;
    graphScopeEveryone?: string;
    graphScopeContacts?: string;
    graphScopeNonContacts?: string;
    graphMatchPeer?: string;
    graphMatchMessage?: string;
    graphMatchModeSubstring?: string;
    graphMatchModeRegex?: string;
}
