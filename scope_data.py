# scope_data.py

# A structured dictionary for all available scopes and their actions
SCOPE_DEFINITIONS = {
    "tcm_sites": {
        "prefix": "tableau:tcm_sites",
        "actions": ["read", "update"],
        "description": "Manage Tableau Cloud Manager sites (view status, update settings)."
    },
    "tcm_users": {
        "prefix": "tableau:tcm_users",
        "actions": ["read", "update"],
        "description": "Manage user accounts at the tenant level (view info, update details)."
    },
    "tcm_groups": {
        "prefix": "tableau:tcm_groups",
        "actions": ["read", "update"],
        "description": "Manage user groups at the tenant level."
    },
    "projects": {
        "prefix": "tableau:projects",
        "actions": ["read", "write"],
        "description": "Manage projects (view, create, update, delete)."
    },
    "datasources": {
        "prefix": "tableau:datasources",
        "actions": ["read", "write", "refresh"],
        "description": "Manage data sources (view, publish, update, delete, refresh)."
    },
    "workbooks": {
        "prefix": "tableau:workbooks",
        "actions": ["read", "write"],
        "description": "Manage workbooks (view, publish, update, delete)."
    },
    "flows": {
        "prefix": "tableau:flows",
        "actions": ["read", "write"],
        "description": "Manage flows (view, publish, update, delete)."
    },
    "metrics": {
        "prefix": "tableau:metrics",
        "actions": ["read", "write"],
        "description": "Manage metrics (view, create, update, delete)."
    },
    "tasks": {
        "prefix": "tableau:tasks",
        "actions": ["read", "write"],
        "description": "Manage scheduled tasks (view, run, update, delete)."
    },
    "subscriptions": {
        "prefix": "tableau:subscriptions",
        "actions": ["read", "write"],
        "description": "Manage subscriptions (view, create, update, delete)."
    },
    "users": {
        "prefix": "tableau:users",
        "actions": ["read", "write"],
        "description": "Manage users on a site (view, add, remove, update)."
    },
    "groups": {
        "prefix": "tableau:groups",
        "actions": ["read", "write"],
        "description": "Manage user groups on a site (view, create, update, delete)."
    },
    "sites": {
        "prefix": "tableau:sites",
        "actions": ["read", "write", "*"],
        "description": "Manage site settings (view, update) or get all permissions with '*'."
    },
    "content": {
        "prefix": "tableau:content",
        "actions": ["read", "write", "*"],
        "description": "Generic access to content (view, create, update, delete) or all with '*'."
    }
}

# Common actions that can be added as a universal option
COMMON_ACTIONS = ["read", "write", "*"]