// SPDX-License-Identifier: 0BSD

export function pluginSlotTextClass(variant: string | undefined): string {
    const map: Record<string, string> = {
        title: "text-xl font-bold tracking-tight text-sem-fg",
        subtitle: "text-base font-semibold text-sem-fg",
        body: "text-sm leading-relaxed text-sem-fg",
        caption: "text-xs text-sem-fg-muted",
        mono: "font-mono text-xs text-sem-fg break-all",
        stat: "text-sm font-medium text-sem-fg",
    };
    return map[variant || "body"] || map.body;
}

export function pluginSlotActionButtonClass(action: { variant?: string } | null | undefined): string {
    const base =
        "inline-flex items-center justify-center px-4 py-2 rounded-lg text-sm font-medium transition-colors focus:outline-hidden focus:ring-2 focus:ring-sem-focus/40 w-fit cursor-pointer";
    if (action?.variant === "secondary") {
        return `${base} secondary-chip border border-sem-border bg-sem-surface text-sem-fg hover:bg-sem-surface-muted`;
    }
    if (action?.variant === "danger") {
        return `${base} danger-chip border border-sem-border bg-sem-surface text-sem-danger hover:bg-sem-danger/10`;
    }
    return `${base} primary-chip bg-sem-action-primary text-white hover:bg-sem-action-primary-hover`;
}

export function pluginSlotRowClass(variant: string | undefined): string {
    if (variant === "path") {
        return "grid grid-cols-1 sm:grid-cols-[minmax(0,1.15fr)_auto_minmax(0,1.35fr)_auto] gap-x-4 gap-y-2 items-center px-4 py-3 text-sm";
    }
    if (variant === "announce") {
        return "grid grid-cols-1 sm:grid-cols-[auto_minmax(0,0.75fr)_minmax(0,1fr)_minmax(0,1.1fr)] gap-x-4 gap-y-2 items-center px-4 py-3 text-sm";
    }
    if (variant === "card") {
        return "grid grid-cols-1 sm:grid-cols-[minmax(0,1.15fr)_auto_minmax(0,1.35fr)_auto] gap-x-4 gap-y-2 items-center px-4 py-3 text-sm bg-sem-surface";
    }
    if (variant === "announce-card") {
        return "grid grid-cols-1 sm:grid-cols-[auto_minmax(0,0.75fr)_minmax(0,1fr)_minmax(0,1.1fr)] gap-x-4 gap-y-2 items-center px-4 py-3 text-sm bg-sem-surface";
    }
    return "flex flex-wrap items-center gap-3 text-sm";
}

export function pluginSlotBadgeClass(variant: string | undefined): string {
    const map: Record<string, string> = {
        success: "bg-sem-success/15 text-sem-success",
        danger: "bg-sem-danger/15 text-sem-danger",
        warning: "bg-sem-warning/15 text-sem-warning",
        info: "bg-sem-info/15 text-sem-info",
        muted: "bg-sem-surface-muted text-sem-fg-muted",
    };
    return map[variant || "muted"] || map.muted;
}

export function pluginSlotSelectOptions(options: unknown): Array<{ value: string; label: string }> {
    if (!Array.isArray(options)) {
        return [];
    }
    return options.map((opt) => {
        if (typeof opt === "string" || typeof opt === "number") {
            return { value: String(opt), label: String(opt) };
        }
        const row = opt as { value?: unknown; label?: unknown };
        return {
            value: String(row.value ?? ""),
            label: String(row.label ?? row.value ?? ""),
        };
    });
}

export function pluginSlotTableColumns(columns: unknown): string[] {
    if (!Array.isArray(columns)) {
        return [];
    }
    return columns.map((c) => (typeof c === "string" ? c : String((c as { label?: string })?.label || "")));
}

export function pluginSlotTableRows(rows: unknown): unknown[][] {
    if (!Array.isArray(rows)) {
        return [];
    }
    return rows.map((row) => {
        if (Array.isArray(row)) {
            return row;
        }
        if (row && typeof row === "object" && Array.isArray((row as { cells?: unknown }).cells)) {
            return (row as { cells: unknown[] }).cells;
        }
        return [];
    });
}
