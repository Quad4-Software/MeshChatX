// SPDX-License-Identifier: 0BSD

export interface NavBadge {
    source?: string;
    pill?: boolean;
    cap?: number;
}

export interface NavRouteTarget {
    name?: string;
    path?: string;
    params?: Record<string, unknown>;
    query?: Record<string, unknown>;
}

export interface NavItem {
    id: string;
    route: NavRouteTarget;
    icon: string;
    label?: string;
    labelKey?: string;
    badge?: NavBadge;
}

export interface NavGroup {
    id: string;
    items: NavItem[];
}

export type NavReorderPayload =
    | { kind: "item"; itemId: string; target: { type: string; id?: string; position?: "before" | "after" } }
    | { kind: "group"; groupId: string; beforeGroupId: string }
    | { kind: "group-offset"; groupId: string; delta: number }
    | { kind: "item-offset"; itemId: string; delta: number };
