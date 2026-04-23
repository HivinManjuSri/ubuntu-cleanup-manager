# core/system_info.py
# This file contains helper functions for reading system information.

import os
import shutil
import subprocess


def bytes_to_human(num_bytes):
    """
    Convert bytes to a human-readable string.
    Example:
        1073741824 -> 1.00 GB
    """
    step = 1024.0
    units = ["B", "KB", "MB", "GB", "TB"]

    size = float(num_bytes)
    for unit in units:
        if size < step:
            return f"{size:.2f} {unit}"
        size /= step

    return f"{size:.2f} PB"


def get_os_info():
    """
    Read OS information from /etc/os-release.

    Returns:
        dict:
            {
                "name": "...",
                "version": "...",
                "codename": "...",
                "pretty_name": "..."
            }
    """
    result = {
        "name": "Unknown",
        "version": "Unknown",
        "codename": "Unknown",
        "pretty_name": "Unknown"
    }

    try:
        with open("/etc/os-release", "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()

                if line.startswith("NAME="):
                    result["name"] = line.split("=", 1)[1].strip('"')

                elif line.startswith("VERSION_ID="):
                    result["version"] = line.split("=", 1)[1].strip('"')

                elif line.startswith("VERSION_CODENAME="):
                    result["codename"] = line.split("=", 1)[1].strip('"')

                elif line.startswith("PRETTY_NAME="):
                    result["pretty_name"] = line.split("=", 1)[1].strip('"')

    except Exception as error:
        result["pretty_name"] = f"Error reading OS info: {error}"

    return result


def get_disk_usage():
    """
    Get disk usage details for the root filesystem (/).

    Returns:
        dict:
            {
                "total": "...",
                "used": "...",
                "free": "..."
            }
    """
    total, used, free = shutil.disk_usage("/")

    return {
        "total": bytes_to_human(total),
        "used": bytes_to_human(used),
        "free": bytes_to_human(free)
    }


def get_cache_size():
    """
    Get the size of the APT package cache.

    Returns:
        str:
            Example: "350M"
            or an error message.
    """
    cache_path = "/var/cache/apt/archives"

    if not os.path.exists(cache_path):
        return "Cache folder not found"

    try:
        result = subprocess.run(
            ["du", "-sh", cache_path],
            capture_output=True,
            text=True,
            check=True
        )

        # Output format is typically:
        # 350M    /var/cache/apt/archives
        return result.stdout.split()[0]

    except Exception as error:
        return f"Error: {error}"


def check_repo_config():
    """
    Perform a simple repository check.

    This is especially useful for Ubuntu 19.04 legacy systems,
    but still okay for newer Ubuntu versions as a simple check.

    Returns:
        dict:
            {
                "ok": True/False,
                "message": "..."
            }
    """
    sources_file = "/etc/apt/sources.list"

    if not os.path.exists(sources_file):
        return {
            "ok": False,
            "message": "/etc/apt/sources.list not found"
        }

    try:
        with open(sources_file, "r", encoding="utf-8") as file:
            content = file.read().lower()

        if "deb " not in content:
            return {
                "ok": False,
                "message": "No active APT repository entries detected"
            }

        # Legacy check for Ubuntu 19.04
        if "disco" in content:
            if "old-releases.ubuntu.com" in content:
                return {
                    "ok": True,
                    "message": "Legacy Ubuntu 19.04 repositories appear configured"
                }
            return {
                "ok": False,
                "message": "Ubuntu 19.04 entries found, but old-releases URL not detected"
            }

        return {
            "ok": True,
            "message": "Repository file looks present and active"
        }

    except Exception as error:
        return {
            "ok": False,
            "message": f"Error reading repository config: {error}"
        }