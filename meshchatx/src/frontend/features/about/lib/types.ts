// SPDX-License-Identifier: 0BSD

export interface AppInfo {
    version?: string;
    display_version?: string;
    is_dev_build?: boolean;
    build_channel?: string;
    git_commit?: string;
    git_commit_short?: string;
    python_version?: string;
    lxmf_version?: string;
    lxst_version?: string;
    rns_version?: string;
    is_connected_to_shared_instance?: boolean;
    shared_instance_address?: string;
    reticulum_config_path?: string | null;
    database_path?: string | null;
    database_file_size?: number;
    database_files?: {
        total_bytes?: number;
    };
    integrity_issues?: string[];
    landlock_requested?: boolean;
    landlock_active?: boolean;
    landlock_auto_enabled?: boolean;
    appcontainer_requested?: boolean;
    appcontainer_active?: boolean;
    appcontainer_supported?: boolean;
    seccomp_requested?: boolean;
    seccomp_active?: boolean;
    seccomp_kernel_supported?: boolean;
    dependencies?: Record<string, string>;
    memory_usage?: {
        rss?: number;
        vms?: number;
        cpu_percent?: number | null;
        num_threads?: number | null;
        create_time?: number;
    };
    battery_usage?: {
        avg_cpu_percent?: number;
        machine_share_percent?: number;
        estimated_percent_per_hour?: number;
        intensity?: string;
        confidence?: string;
        method?: string;
    };
    resource_breakdown?: Array<{
        name: string;
        rss?: number;
        cpu_percent?: number;
    }>;
    reticulum_stats?: {
        total_paths?: number;
        memory_cleanup?: {
            path_table_size?: number;
            sqlite_relaxed?: boolean;
        };
    };
    channel_prompt?: {
        notes?: string;
        focus_areas?: string[];
        bug_report_steps?: string[];
        target?: {
            kind?: string;
            value?: string;
        };
        lxmf_target?: string;
        url_target?: string;
    };
}

export interface ActiveSession {
    id: string;
    ip?: string;
    user_agent?: string;
    connected_at?: number;
}

export interface DatabaseHealth {
    quick_check?: string;
    journal_mode?: string;
    page_size?: number;
    page_count?: number;
    freelist_pages?: number;
    estimated_free_bytes?: number;
    integrity_check?: string;
}

export interface DatabaseRecoveryAction {
    step: string;
    result: unknown;
}

export interface SnapshotItem {
    name: string;
    path: string;
    size: number;
    created_at: number;
}

export interface AutoBackupItem {
    name: string;
    path: string;
    size: number;
    created_at: number;
}

export interface SandboxFeatureCard {
    id: string;
    active: boolean;
    warn?: boolean;
    unavailable?: boolean;
    titleKey: string;
    badgeKey: string;
    noteKey: string;
}
