"""Built-in wordlists of commonly-exposed / sensitive paths.

Each entry carries metadata so the engine can assign a severity and a
human-readable reason to any hit, instead of just dumping status codes.

Severity scale (high -> low): critical, high, medium, low, info
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Entry format: (path, category, severity, description)
# `path` is relative and is joined onto the target's base path.
# ---------------------------------------------------------------------------

_ENTRIES = [
    # --- Version control systems (leak full source + history) ----------------
    (".git/", "vcs", "critical", "Exposed Git repository directory"),
    (".git/config", "vcs", "critical", "Git config — reveals remotes/credentials"),
    (".git/HEAD", "vcs", "critical", "Git HEAD — confirms repo is downloadable"),
    (".git/index", "vcs", "critical", "Git index — lets attackers reconstruct source"),
    (".git/logs/HEAD", "vcs", "high", "Git reflog — commit history leak"),
    (".svn/", "vcs", "high", "Exposed Subversion directory"),
    (".svn/entries", "vcs", "high", "Subversion metadata leak"),
    (".hg/", "vcs", "high", "Exposed Mercurial directory"),
    (".bzr/", "vcs", "medium", "Exposed Bazaar directory"),

    # --- Secrets / environment / credentials --------------------------------
    (".env", "secrets", "critical", "Environment file — API keys, DB creds"),
    (".env.local", "secrets", "critical", "Local environment file with secrets"),
    (".env.production", "secrets", "critical", "Production environment secrets"),
    (".env.dev", "secrets", "high", "Development environment secrets"),
    (".env.backup", "secrets", "critical", "Backup of environment secrets"),
    ("config.php", "secrets", "high", "PHP config — often contains DB creds"),
    ("wp-config.php", "secrets", "high", "WordPress config with DB password"),
    ("wp-config.php.bak", "secrets", "critical", "Readable WordPress config backup"),
    ("configuration.php", "secrets", "high", "Joomla config with DB creds"),
    ("settings.py", "secrets", "high", "Django settings — SECRET_KEY, DB creds"),
    ("local_settings.py", "secrets", "high", "Django local settings with secrets"),
    ("appsettings.json", "secrets", "high", ".NET config — connection strings"),
    ("application.properties", "secrets", "high", "Spring config with credentials"),
    ("application.yml", "secrets", "high", "Spring/YAML config with credentials"),
    ("credentials", "secrets", "critical", "Credentials file"),
    (".aws/credentials", "secrets", "critical", "AWS access keys"),
    (".npmrc", "secrets", "medium", "npm config — may contain auth token"),
    (".dockercfg", "secrets", "high", "Docker registry credentials"),
    (".docker/config.json", "secrets", "high", "Docker registry credentials"),
    ("secrets.json", "secrets", "critical", "Secrets file"),
    ("secrets.yml", "secrets", "critical", "Secrets file"),
    ("id_rsa", "secrets", "critical", "Private SSH key"),
    ("id_dsa", "secrets", "critical", "Private SSH key"),
    (".ssh/id_rsa", "secrets", "critical", "Private SSH key"),
    (".htpasswd", "secrets", "high", "Basic-auth password hashes"),

    # --- Backups / dumps (whole-site or DB exposure) ------------------------
    ("backup/", "backup", "high", "Backup directory"),
    ("backups/", "backup", "high", "Backup directory"),
    ("backup.zip", "backup", "critical", "Full-site backup archive"),
    ("backup.tar.gz", "backup", "critical", "Full-site backup archive"),
    ("backup.sql", "backup", "critical", "Database backup"),
    ("db.sql", "backup", "critical", "Database dump"),
    ("dump.sql", "backup", "critical", "Database dump"),
    ("database.sql", "backup", "critical", "Database dump"),
    ("site.zip", "backup", "critical", "Site archive"),
    ("www.zip", "backup", "critical", "Site archive"),
    ("backup.bak", "backup", "high", "Backup file"),
    ("index.php.bak", "backup", "high", "Source backup — readable as text"),
    ("index.html.bak", "backup", "medium", "Page backup"),
    ("web.config.bak", "backup", "high", "IIS config backup"),
    ("old/", "backup", "medium", "Old/archived content directory"),
    (".bak", "backup", "medium", "Backup file"),

    # --- Admin / control panels ---------------------------------------------
    ("admin/", "admin", "medium", "Admin area"),
    ("admin/login", "admin", "medium", "Admin login page"),
    ("administrator/", "admin", "medium", "Admin area (Joomla)"),
    ("wp-admin/", "admin", "low", "WordPress admin"),
    ("wp-login.php", "admin", "low", "WordPress login"),
    ("phpmyadmin/", "admin", "high", "phpMyAdmin — direct DB access"),
    ("pma/", "admin", "high", "phpMyAdmin alias"),
    ("adminer.php", "admin", "high", "Adminer — direct DB access"),
    ("manager/html", "admin", "high", "Tomcat manager"),
    ("console/", "admin", "medium", "Admin console"),
    ("dashboard/", "admin", "low", "Dashboard"),

    # --- Info disclosure -----------------------------------------------------
    ("phpinfo.php", "info-disclosure", "high", "phpinfo() — full server config leak"),
    ("info.php", "info-disclosure", "high", "phpinfo() — full server config leak"),
    ("test.php", "info-disclosure", "medium", "Test script — often phpinfo()"),
    ("server-status", "info-disclosure", "high", "Apache server-status — live requests"),
    ("server-info", "info-disclosure", "high", "Apache server-info — config leak"),
    (".DS_Store", "info-disclosure", "medium", "macOS metadata — leaks file listing"),
    ("robots.txt", "info-disclosure", "info", "robots.txt — may reveal hidden paths"),
    ("sitemap.xml", "info-disclosure", "info", "Sitemap — enumerates URLs"),
    ("crossdomain.xml", "info-disclosure", "low", "Flash cross-domain policy"),
    (".well-known/security.txt", "info-disclosure", "info", "security.txt contact file"),
    ("package.json", "info-disclosure", "low", "Dependency manifest — version leak"),
    ("composer.json", "info-disclosure", "low", "PHP dependency manifest"),
    ("composer.lock", "info-disclosure", "low", "Locked dependency versions"),

    # --- Logs ----------------------------------------------------------------
    ("error.log", "logs", "high", "Error log — paths, stack traces"),
    ("errors.log", "logs", "high", "Error log"),
    ("access.log", "logs", "medium", "Access log"),
    ("debug.log", "logs", "high", "Debug log — may contain secrets"),
    ("logs/", "logs", "medium", "Log directory"),
    ("laravel.log", "logs", "high", "Laravel log — stack traces & secrets"),
    ("storage/logs/laravel.log", "logs", "high", "Laravel log"),
    ("npm-debug.log", "logs", "low", "npm debug log"),

    # --- Deployment / CI -----------------------------------------------------
    ("Dockerfile", "deployment", "low", "Dockerfile — build details"),
    ("docker-compose.yml", "deployment", "medium", "Compose file — services & creds"),
    (".gitlab-ci.yml", "deployment", "medium", "GitLab CI config — may hold tokens"),
    (".github/workflows/", "deployment", "low", "GitHub Actions workflows"),
    (".travis.yml", "deployment", "low", "Travis CI config"),
    ("Makefile", "deployment", "low", "Makefile — build/deploy commands"),
    ("web.config", "deployment", "medium", "IIS config"),
    (".htaccess", "deployment", "medium", "Apache rules — reveals rewrite/auth"),

    # --- Directories likely to have listing enabled -------------------------
    ("uploads/", "directory-listing", "medium", "Uploads directory"),
    ("files/", "directory-listing", "medium", "Files directory"),
    ("images/", "directory-listing", "low", "Images directory"),
    ("img/", "directory-listing", "low", "Images directory"),
    ("assets/", "directory-listing", "low", "Assets directory"),
    ("static/", "directory-listing", "low", "Static assets directory"),
    ("tmp/", "directory-listing", "medium", "Temp directory"),
    ("temp/", "directory-listing", "medium", "Temp directory"),
    ("private/", "directory-listing", "high", "Private directory"),
    ("data/", "directory-listing", "medium", "Data directory"),
    ("includes/", "directory-listing", "medium", "Includes directory"),
    ("vendor/", "directory-listing", "low", "Dependency directory"),
    ("node_modules/", "directory-listing", "low", "Node dependency directory"),
    ("cgi-bin/", "directory-listing", "medium", "CGI directory"),
]

# ---------------------------------------------------------------------------
# Named wordlist profiles selectable from the UI/CLI.
# ---------------------------------------------------------------------------

_PROFILE_CATEGORIES = {
    "sensitive": {"vcs", "secrets", "backup"},
    "config": {"vcs", "secrets", "backup", "config", "deployment"},
    "directories": {"directory-listing", "admin"},
    "info": {"info-disclosure", "logs"},
}


def all_entries():
    """Return every built-in entry as a list of dicts."""
    return [
        {"path": p, "category": c, "severity": s, "description": d}
        for (p, c, s, d) in _ENTRIES
    ]


def profile(name: str):
    """Return entries for a named profile.

    'common' / 'full' -> everything. Otherwise filter by category group.
    """
    name = (name or "common").lower()
    entries = all_entries()
    if name in ("common", "full", "all"):
        return entries
    cats = _PROFILE_CATEGORIES.get(name)
    if not cats:
        return entries
    return [e for e in entries if e["category"] in cats]


def profile_names():
    return ["common", "sensitive", "config", "directories", "info"]


# Content signatures: if a body from `path` matches, we *confirm* the finding
# and can bump severity. Keys are substrings of the path; values are
# (needle, note) with needle matched case-insensitively against the body.
CONTENT_SIGNATURES = {
    ".env": ("=", "environment key=value pairs present"),
    ".git/config": ("[core]", "valid git config content"),
    ".git/HEAD": ("ref:", "valid git HEAD content"),
    "wp-config": ("DB_PASSWORD", "database password present"),
    "phpinfo": ("PHP Version", "live phpinfo() output"),
    "info.php": ("PHP Version", "live phpinfo() output"),
    "server-status": ("Apache Server Status", "live server-status output"),
    ".sql": ("CREATE TABLE", "SQL dump content"),
    "dump": ("INSERT INTO", "SQL dump content"),
    "id_rsa": ("PRIVATE KEY", "private key material"),
    ".htpasswd": (":", "password hash entries"),
    ".DS_Store": ("Bud1", "valid .DS_Store metadata"),
    "credentials": ("secret", "credential material"),
}

# Signatures that indicate an auto-generated directory listing is enabled.
DIRECTORY_LISTING_SIGNATURES = [
    "Index of /",
    "<title>Index of",
    "Directory listing for",
    "Parent Directory",
    "[To Parent Directory]",  # IIS
]
