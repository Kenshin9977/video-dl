from platform import machine
from re import IGNORECASE, search


def get_system_architecture() -> str:
    """
    Get the streamlined name of the current system architecture.

    Returns:
        str: The streamlined name of the current system architecture.
    """
    architecture = machine()
    if search("arm64|aarch64", architecture, IGNORECASE):
        return "arm64"
    elif search("arm", architecture, IGNORECASE):
        return "arm"
    elif search("x86_64|amd64", architecture, IGNORECASE):
        return "x86_64"
    elif search("86", architecture, IGNORECASE):
        return "x86"
    return "unknown"


ARCHITECTURE = get_system_architecture()
