"""Server constants."""

# System directories that cannot be deleted or renamed.
# EXPORT/INBOX/SCREENSHOT use all-caps to match the Supernote device firmware.
IMMUTABLE_SYSTEM_DIRECTORIES = {
    "EXPORT",
    "INBOX",
    "SCREENSHOT",
    "Note",
    "Document",
    "MyStyle",
    "NOTE",  # Category container
    "DOCUMENT",  # Category container
}

# Category containers (hidden from web API)
CATEGORY_CONTAINERS = {"NOTE", "DOCUMENT"}

# Forced order and specific names for web API root (when flatten=True)
ORDERED_WEB_ROOT = ["Note", "Document"]

# Maps real (device-facing) folder names to their web UI display names
SYSTEM_DIR_DISPLAY_NAMES: dict[str, str] = {
    "EXPORT": "Export",
    "INBOX": "Inbox",
    "SCREENSHOT": "Screenshot",
}

# Names that appear immutable from the web API's perspective (uses display names)
WEB_IMMUTABLE_NAMES: frozenset[str] = frozenset(
    SYSTEM_DIR_DISPLAY_NAMES.get(name, name) for name in IMMUTABLE_SYSTEM_DIRECTORIES
)

# Blob Storage Buckets
USER_DATA_BUCKET = "supernote-user-data"
CACHE_BUCKET = "supernote-cache"

# Maximum upload size for file uploads
MAX_UPLOAD_SIZE = 1024 * 1024 * 1024  # 1GB
