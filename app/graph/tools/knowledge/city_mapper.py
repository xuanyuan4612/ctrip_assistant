"""City name resolution — database-driven Chinese/English city lookup.

Replaces the hardcoded dictionary in ``tools/location_trans.py`` with a
flexible approach:

1. **Database table** ``city_mappings`` (preferred) — queried at runtime.
2. **In-memory fallback dict** — used when the table is unavailable
   (e.g. during testing before schema migration).

The agent layer calls ``resolve_city(name)`` whenever a tool needs to
normalise a user-supplied location string (e.g. "北京" → "Beijing").
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Optional

from app.graph.tools.types import TEMP_SQLITE_PATH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static fallback dictionary
# ---------------------------------------------------------------------------
# Mirrors the legacy ``tools/location_trans.py`` mapping.  The database
# table ``city_mappings`` should become the single source of truth once
# the schema migration is applied.
# TODO: Remove this dict once the ``city_mappings`` table is available
#       in the SQLite / MySQL schema and the DB-driven path is proven.
_FALLBACK_CITY_MAP: dict[str, str] = {
    "北京": "Beijing",
    "上海": "Shanghai",
    "广州": "Guangzhou",
    "深圳": "Shenzhen",
    "成都": "Chengdu",
    "杭州": "Hangzhou",
    "巴塞尔": "Basel",
    "苏黎世": "Zurich",
}


def _is_chinese(text: str) -> bool:
    """Return ``True`` if every character in *text* falls in the CJK range."""
    return all("\u4e00" <= char <= "\u9fff" for char in text)


def _lookup_from_db(chinese_name: str) -> Optional[str]:
    """Try to resolve *chinese_name* via the ``city_mappings`` table.

    Returns the English name if found, or ``None`` if the table doesn't
    exist or the name is absent.
    """
    # TODO: Replace with MySQL Repository call:
    #   CityMappingRepository.get_english_name(chinese_name)
    try:
        conn = sqlite3.connect(TEMP_SQLITE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT english_name FROM city_mappings WHERE chinese_name = ?",
            (chinese_name,),
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        logger.debug("city_mappings table not available — using fallback dict")
        return None


def resolve_city(name: Optional[str]) -> Optional[str]:
    """Normalise a city name to its English form.

    Resolution strategy (in order of precedence):

    1. If *name* is ``None`` or empty → return as-is.
    2. If *name* contains no CJK characters → already English, return
       unchanged.
    3. Try the ``city_mappings`` database table.
    4. Fall back to the static dictionary.

    Args:
        name: Raw city name from the user (e.g. ``"北京"``,
            ``"Basel"``, ``None``).

    Returns:
        Normalised English city name, or the original string if no
        mapping was found.
    """
    if not name:
        return name

    if not _is_chinese(name):
        return name  # Already English / non-CJK.

    # Try database first, then fallback dict.
    db_result = _lookup_from_db(name)
    if db_result:
        return db_result

    fallback = _FALLBACK_CITY_MAP.get(name)
    if fallback:
        logger.debug("Resolved city via fallback dict: %s → %s", name, fallback)
        return fallback

    logger.warning("Unrecognised Chinese city name: %s", name)
    return name  # Return original if unresolvable


__all__ = ["resolve_city"]
