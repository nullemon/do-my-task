"""webscan — a read-only website exposure scanner.

Find exposed URLs, directories, config files, backups and secrets on sites
you own or are authorized to test, so you can lock them down.
"""

__version__ = "1.0.0"

from .engine import ScanConfig, scan, scan_collect  # noqa: F401
