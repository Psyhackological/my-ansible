#!/usr/bin/python
# -*- coding: utf-8 -*-

DOCUMENTATION = """
---
module: uv_tool
short_description: Manages Python tools with uv tool
description:
    - Manages Python tools with uv tool, the fast Python package installer and resolver
options:
    name:
        description:
            - The name of a Python tool to install/remove
        required: true
        type: str
    state:
        description:
            - The state of the Python tool
        required: false
        default: present
        choices: [ "present", "absent", "latest" ]
        type: str
    executable:
        description:
            - Path to uv executable
        default: uv
        type: str
    extra_args:
        description:
            - Extra arguments to pass to uv
        type: str
    no_cache:
        description:
            - Avoid reading from or writing to the cache
        required: false
        default: false
        type: bool
    cache_dir:
        description:
            - Path to the cache directory
        required: false
        type: str
    project:
        description:
            - Run the command within the given project directory
        required: false
        type: str
    debug:
        description:
            - Enable debug output
        required: false
        default: false
        type: bool
"""

EXAMPLES = """
# Install a tool
- uv_tool:
    name: black

# Upgrade installed tool
- uv_tool:
    name: black
    state: latest

# Remove a tool
- uv_tool:
    name: black
    state: absent
"""

RETURN = """
cmd:
    description: The command used to manage the tool
    returned: success
    type: str
    sample: "/home/user/.local/bin/uv tool install black"
name:
    description: The tool name
    returned: success
    type: str
    sample: "black"
debug_info:
    description: Debug information about the module execution
    returned: when debug=true
    type: dict
"""

import os
import re
from ansible.module_utils.basic import AnsibleModule


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type="str", required=True),
            state=dict(
                type="str", default="present", choices=["present", "absent", "latest"]
            ),
            executable=dict(type="str", default="uv"),
            extra_args=dict(type="str", default=""),
            no_cache=dict(type="bool", default=False),
            cache_dir=dict(type="str"),
            project=dict(type="str"),
            debug=dict(type="bool", default=False),
        ),
        supports_check_mode=True,
    )

    name = module.params["name"]
    state = module.params["state"]
    executable = module.params["executable"]
    extra_args = module.params["extra_args"]
    no_cache = module.params["no_cache"]
    cache_dir = module.params["cache_dir"]
    project = module.params["project"]
    debug = module.params["debug"]

    # Ensure executable is found
    if executable == "uv":
        executable = module.get_bin_path("uv", required=True)

    # First check if the tool is already installed
    list_cmd = [executable, "tool", "list"]
    list_rc, list_out, list_err = module.run_command(list_cmd)

    # Define patterns to look for in output
    installed_pattern = re.compile(r"Installed [0-9]+ (package|executable)")
    uninstalled_pattern = re.compile(r"Uninstalled [0-9]+ executable")

    # Check if tool is already installed
    tool_already_installed = name in list_out

    # Prepare command based on state
    cmd = [executable, "tool"]

    if state == "present":
        if tool_already_installed and not module.check_mode:
            # Tool is already installed, no action needed
            module.exit_json(
                changed=False,
                cmd=" ".join(list_cmd),
                name=name,
                stdout=f"Tool {name} is already installed",
                stderr="",
                debug_info={"tool_already_installed": True} if debug else {},
            )
        cmd.append("install")
    elif state == "latest":
        cmd.append("upgrade")
    elif state == "absent":
        if not tool_already_installed and not module.check_mode:
            # Tool is not installed, no action needed
            module.exit_json(
                changed=False,
                cmd=" ".join(list_cmd),
                name=name,
                stdout=f"Tool {name} is not installed",
                stderr="",
                debug_info={"tool_already_installed": False} if debug else {},
            )
        cmd.append("uninstall")

    # Add global options
    if no_cache:
        cmd.append("--no-cache")

    if cache_dir:
        cmd.append("--cache-dir")
        cmd.append(cache_dir)

    if project:
        cmd.append("--project")
        cmd.append(project)

    if extra_args:
        cmd.append(extra_args)

    # Add tool name
    cmd.append(name)

    if module.check_mode:
        module.exit_json(
            changed=True,
            cmd=" ".join(cmd),
            name=name,
            debug_info={"check_mode": True} if debug else {},
        )

    rc, out, err = module.run_command(cmd)

    # Combine stdout and stderr for pattern matching
    combined_output = out + err

    # Debug info to help troubleshoot
    debug_info = {
        "state": state,
        "tool_already_installed": tool_already_installed,
        "out_contains_installed": bool(installed_pattern.search(out)),
        "err_contains_installed": bool(installed_pattern.search(err)),
        "combined_contains_installed": bool(installed_pattern.search(combined_output)),
        "out_contains_uninstalled": bool(uninstalled_pattern.search(out)),
        "err_contains_uninstalled": bool(uninstalled_pattern.search(err)),
        "combined_contains_uninstalled": bool(uninstalled_pattern.search(combined_output)),
        "out_length": len(out),
        "out_first_100_chars": out[:100] if out else "",
        "err_length": len(err),
        "err_first_100_chars": err[:100] if err else "",
        "rc": rc,
    } if debug else {}

    if rc != 0:
        # Check if the error is because the tool is already installed
        if "already installed" in err:
            module.exit_json(
                changed=False,
                cmd=" ".join(cmd),
                name=name,
                stdout=out,
                stderr=err,
                debug_info=debug_info,
            )
        module.fail_json(
            msg="Failed to execute uv tool",
            cmd=" ".join(cmd),
            stdout=out,
            stderr=err,
            rc=rc,
            debug_info=debug_info,
        )

    # Determine if a change was made by checking both stdout and stderr
    changed = False
    if state == "present":
        changed = bool(installed_pattern.search(combined_output))
    elif state == "latest":
        # For upgrade, any output usually means something was upgraded
        changed = len(combined_output.strip()) > 0 and "Nothing to upgrade" not in combined_output
    elif state == "absent":
        changed = bool(uninstalled_pattern.search(combined_output))

    module.exit_json(
        changed=changed,
        cmd=" ".join(cmd),
        name=name,
        stdout=out,
        stderr=err,
        debug_info=debug_info,
    )


if __name__ == "__main__":
    main()

