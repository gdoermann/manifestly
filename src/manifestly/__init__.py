"""
Manifestly is a Python library for creating and managing manifest files.
"""
from .core import Manifest

__version__ = "0.2.2"


def get_version():
    """
    Get the version of the library
    :return: MAJOR.MINOR.PATCH version
    """
    return __version__


__all__ = ["Manifest", "get_version"]
