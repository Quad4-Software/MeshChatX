"""Permissions system for LXMFy."""

from dataclasses import dataclass, field
from enum import Flag, auto
from typing import Any


class BasePermission(Flag):
    """Base permission flags"""

    NONE = 0
    READ = auto()
    WRITE = auto()
    EXECUTE = auto()
    MANAGE = auto()
    ALL = READ | WRITE | EXECUTE | MANAGE


class DefaultPerms(Flag):
    """Default permission set"""

    NONE = 0
    # Basic permissions
    USE_BOT = auto()
    SEND_MESSAGES = auto()
    USE_COMMANDS = auto()

    # Elevated permissions
    MANAGE_MESSAGES = auto()
    MANAGE_COMMANDS = auto()
    MANAGE_USERS = auto()

    # Special permissions
    BYPASS_RATELIMIT = auto()
    BYPASS_SPAM = auto()
    VIEW_ADMIN_COMMANDS = auto()

    # Event system permissions
    VIEW_EVENTS = auto()
    MANAGE_EVENTS = auto()
    BYPASS_EVENT_CHECKS = auto()

    # Combined permissions
    ALL = (
        USE_BOT
        | SEND_MESSAGES
        | USE_COMMANDS
        | MANAGE_MESSAGES
        | MANAGE_COMMANDS
        | MANAGE_USERS
        | BYPASS_RATELIMIT
        | BYPASS_SPAM
        | VIEW_ADMIN_COMMANDS
        | VIEW_EVENTS
        | MANAGE_EVENTS
        | BYPASS_EVENT_CHECKS
    )


@dataclass
class Role:
    """Role definition with permissions"""

    name: str
    permissions: DefaultPerms
    priority: int = 0
    description: str | None = None


@dataclass
class PermissionManager:
    """Manages permissions, roles, and user assignments"""

    storage: Any
    enabled: bool = False
    default_role: Role = field(
        default_factory=lambda: Role(
            "user",
            DefaultPerms.USE_BOT
            | DefaultPerms.SEND_MESSAGES
            | DefaultPerms.USE_COMMANDS,
        ),
    )
    admin_role: Role = field(
        default_factory=lambda: Role("admin", DefaultPerms.ALL, priority=100),
    )

    def __post_init__(self):
        self.roles: dict[str, Role] = {
            "user": self.default_role,
            "admin": self.admin_role,
        }
        self.user_roles: dict[str, set[str]] = {}
        self.load_data()

    def load_data(self):
        """Load permission data from storage"""
        stored_roles = self.storage.get("permissions:roles", {})
        stored_user_roles = self.storage.get("permissions:user_roles", {})

        # Convert stored roles back to Role objects
        for role_name, role_data in stored_roles.items():
            if role_name not in ["user", "admin"]:  # Don't override default/admin
                self.roles[role_name] = Role(
                    name=role_data["name"],
                    permissions=DefaultPerms(role_data["permissions"]),
                    priority=role_data["priority"],
                    description=role_data.get("description"),
                )

        self.user_roles = {
            user: set(roles) for user, roles in stored_user_roles.items()
        }

    def save_data(self):
        """Save permission data to storage"""
        # Convert roles to serializable format
        roles_data = {
            name: {
                "name": role.name,
                "permissions": role.permissions.value,
                "priority": role.priority,
                "description": role.description,
            }
            for name, role in self.roles.items()
        }

        self.storage.set("permissions:roles", roles_data)
        self.storage.set(
            "permissions:user_roles",
            {user: list(roles) for user, roles in self.user_roles.items()},
        )

    def create_role(
        self,
        name: str,
        permissions: DefaultPerms,
        priority: int = 0,
        description: str | None = None,
    ) -> Role:
        """Create a new role"""
        if name in self.roles:
            raise ValueError(f"Role {name} already exists")

        role = Role(name, permissions, priority, description)
        self.roles[name] = role
        self.save_data()
        return role

    def delete_role(self, name: str) -> bool:
        """Delete a role"""
        if name in ["user", "admin"]:
            raise ValueError("Cannot delete default or admin roles")

        if name in self.roles:
            del self.roles[name]
            # Remove role from all users
            for user_roles in self.user_roles.values():
                user_roles.discard(name)
            self.save_data()
            return True
        return False

    def assign_role(self, user: str, role_name: str):
        """Assign a role to a user"""
        if role_name not in self.roles:
            raise ValueError(f"Role {role_name} does not exist")

        if user not in self.user_roles:
            self.user_roles[user] = {self.default_role.name}

        self.user_roles[user].add(role_name)
        self.save_data()

    def remove_role(self, user: str, role_name: str):
        """Remove a role from a user"""
        if (
            user in self.user_roles
            and role_name in self.user_roles[user]
            and role_name != self.default_role.name
        ):
            self.user_roles[user].remove(role_name)
            self.save_data()

    def get_user_permissions(self, user: str) -> DefaultPerms:
        """Get combined permissions for a user"""
        if user not in self.user_roles:
            return self.default_role.permissions

        perms = DefaultPerms.NONE
        for role_name in self.user_roles[user]:
            if role_name in self.roles:
                perms |= self.roles[role_name].permissions

        return perms

    def has_permission(self, user: str, permission: DefaultPerms) -> bool:
        """Check if user has specific permission"""
        if not self.enabled:
            return True
        user_perms = self.get_user_permissions(user)
        return (user_perms & permission) == permission
