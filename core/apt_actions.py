# core/apt_actions.py
# This file contains functions that run APT commands
# and return structured results.

import subprocess


def run_command(command, require_privilege=False):
    """
    Run a shell command and return structured output.

    Args:
        command (str): Command to run
        require_privilege (bool): If True, run with pkexec

    Returns:
        dict:
            {
                "success": bool,
                "command": str,
                "stdout": str,
                "stderr": str,
                "exit_code": int
            }
    """
    if require_privilege:
        full_command = ["pkexec", "/bin/bash", "-lc", command]
    else:
        full_command = ["/bin/bash", "-lc", command]

    try:
        completed = subprocess.run(
            full_command,
            capture_output=True,
            text=True
        )

        return {
            "success": completed.returncode == 0,
            "command": command,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
            "exit_code": completed.returncode
        }

    except Exception as error:
        return {
            "success": False,
            "command": command,
            "stdout": "",
            "stderr": str(error),
            "exit_code": -1
        }


def run_apt_update():
    """
    Refresh package lists.
    Requires admin privilege.
    """
    return run_command("apt update", require_privilege=True)


def get_upgradable_packages():
    """
    Get the list of packages that can be upgraded.

    Returns:
        dict with extra fields:
            "packages": list
            "count": int
    """
    result = run_command("apt list --upgradable 2>/dev/null", require_privilege=False)

    packages = []

    if result["success"]:
        for line in result["stdout"].splitlines():
            line = line.strip()

            # Skip empty lines and the "Listing..." header
            if not line or line.lower().startswith("listing"):
                continue

            packages.append(line)

    result["packages"] = packages
    result["count"] = len(packages)

    return result


def run_autoclean():
    """
    Remove obsolete package files from the APT cache.
    Requires admin privilege.
    """
    return run_command("apt autoclean", require_privilege=True)


def run_clean():
    """
    Remove all downloaded package files from the APT cache.
    Requires admin privilege.
    """
    return run_command("apt clean", require_privilege=True)


def run_autoremove():
    """
    Remove packages that were automatically installed
    and are no longer needed.
    Requires admin privilege.
    """
    return run_command("apt autoremove -y", require_privilege=True)