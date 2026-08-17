"""Lithology classification for formation names.

Lazy-loaded, cached provider with three layers:
1. Builtin seed dict of known MT formations
2. BigQuery cache table (formation_lithology)
3. GenaiClient LLM fallback for unknown formations
"""

import json
import logging

from mt_oil.config import settings
from mt_oil.schemas.lithology import LithologyResult

logger = logging.getLogger(__name__)

# ── Layer 1: Builtin seed dict ────────────────────────────────────────────────
# Source: USGS, MBOGC records, regional lithology maps for Montana formations

BUILTIN_LITHOLOGY: dict[str, dict] = {
    # Williston Basin carbonate formations
    "red river": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.95},
    "red river b": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.95},
    "red river c": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.95},
    "red river d": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.95},
    "red river e": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.95},
    "red river f": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.95},
    "red river g": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.95},
    "red river h": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.95},
    "stony mountain": {
        "lithology": "carbonate",
        "is_carbonate": True,
        "confidence": 0.90,
    },
    "winnipegosis": {
        "lithology": "carbonate",
        "is_carbonate": True,
        "confidence": 0.90,
    },
    "dawson bay": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.90},
    "ratcliffe": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.85},
    "tilston": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.85},
    "frobisher": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.85},
    "alida": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.85},
    "middle": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.85},
    "kinderhookian": {
        "lithology": "carbonate",
        "is_carbonate": True,
        "confidence": 0.80,
    },
    "lodgpole": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.95},
    "mission canyon": {
        "lithology": "carbonate",
        "is_carbonate": True,
        "confidence": 0.95,
    },
    "madison": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.95},
    "charles": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.90},
    "poplar": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.85},
    "duprow": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.80},
    "kibbey": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.80},
    "othell": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.85},
    "jefferson": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.90},
    "birdbear": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.90},
    "nisku": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.90},
    "duperow": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.85},
    "grosmont": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.85},
    "interlake": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.90},
    "silurian": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.80},
    "devonian": {"lithology": "carbonate", "is_carbonate": True, "confidence": 0.80},
    # Mixed / dolomitic carbonate-siliciclastic
    "three forks": {
        "lithology": "mixed carbonate-siliciclastic",
        "is_carbonate": True,
        "confidence": 0.80,
    },
    "three forks b": {
        "lithology": "mixed carbonate-siliciclastic",
        "is_carbonate": True,
        "confidence": 0.80,
    },
    "three forks c": {
        "lithology": "mixed carbonate-siliciclastic",
        "is_carbonate": True,
        "confidence": 0.80,
    },
    "sanish": {
        "lithology": "mixed carbonate-siliciclastic",
        "is_carbonate": False,
        "confidence": 0.75,
    },
    "false bakken": {
        "lithology": "siliciclastic",
        "is_carbonate": False,
        "confidence": 0.85,
    },
    "scallion": {
        "lithology": "siliciclastic",
        "is_carbonate": False,
        "confidence": 0.80,
    },
    # Siliciclastic (Bakken, etc.)
    "bakken": {"lithology": "siliciclastic", "is_carbonate": False, "confidence": 0.95},
    "upper bakken": {
        "lithology": "siliciclastic",
        "is_carbonate": False,
        "confidence": 0.95,
    },
    "middle bakken": {
        "lithology": "siliciclastic",
        "is_carbonate": False,
        "confidence": 0.95,
    },
    "lower bakken": {
        "lithology": "siliciclastic",
        "is_carbonate": False,
        "confidence": 0.95,
    },
    "pronghorn": {
        "lithology": "siliciclastic",
        "is_carbonate": False,
        "confidence": 0.80,
    },
    "spearfish": {
        "lithology": "siliciclastic",
        "is_carbonate": False,
        "confidence": 0.85,
    },
    "tensleep": {
        "lithology": "siliciclastic",
        "is_carbonate": False,
        "confidence": 0.90,
    },
    "minnelusa": {
        "lithology": "siliciclastic",
        "is_carbonate": False,
        "confidence": 0.90,
    },
    "cloverly": {
        "lithology": "siliciclastic",
        "is_carbonate": False,
        "confidence": 0.85,
    },
    "muddy": {"lithology": "siliciclastic", "is_carbonate": False, "confidence": 0.85},
    "dakota": {"lithology": "siliciclastic", "is_carbonate": False, "confidence": 0.85},
    "fall river": {
        "lithology": "siliciclastic",
        "is_carbonate": False,
        "confidence": 0.85,
    },
    "kootenai": {
        "lithology": "siliciclastic",
        "is_carbonate": False,
        "confidence": 0.80,
    },
    "bow island": {
        "lithology": "siliciclastic",
        "is_carbonate": False,
        "confidence": 0.80,
    },
    "eagle": {"lithology": "siliciclastic", "is_carbonate": False, "confidence": 0.85},
    "virgelle": {
        "lithology": "siliciclastic",
        "is_carbonate": False,
        "confidence": 0.80,
    },
    "telegraph creek": {
        "lithology": "siliciclastic",
        "is_carbonate": False,
        "confidence": 0.80,
    },
    "judith river": {
        "lithology": "siliciclastic",
        "is_carbonate": False,
        "confidence": 0.80,
    },
    "hell creek": {
        "lithology": "siliciclastic",
        "is_carbonate": False,
        "confidence": 0.85,
    },
    "fort union": {
        "lithology": "siliciclastic",
        "is_carbonate": False,
        "confidence": 0.85,
    },
    "wasatch": {
        "lithology": "siliciclastic",
        "is_carbonate": False,
        "confidence": 0.85,
    },
    "tongue river": {
        "lithology": "siliciclastic",
        "is_carbonate": False,
        "confidence": 0.80,
    },
    # Evaporite
    "prairie": {"lithology": "evaporite", "is_carbonate": False, "confidence": 0.90},
    # Chalk
    "niobrara": {"lithology": "chalk", "is_carbonate": True, "confidence": 0.90},
    # Unknown / generic
    "unknown": {"lithology": "unknown", "is_carbonate": False, "confidence": 0.0},
}

# In-memory cache hit by formation_name (lowercase)
_cache: dict[str, LithologyResult] = {}

# LLM helper prompt
LLM_PROMPT = """You are a petroleum geology classifier. Determine if the given formation name is a carbonate lithology (limestone, dolomite, chalk, or carbonate-dominated mixed lithology).

Respond with valid JSON: {{"lithology": str, "is_carbonate": bool, "confidence": float, "reasoning": str}}

Formation name: {formation}"""


def _key(name: str) -> str:
    return name.strip().lower()


def _lookup_builtin(name: str) -> LithologyResult | None:
    entry = BUILTIN_LITHOLOGY.get(_key(name))
    if entry:
        return LithologyResult(**entry)
    return None


def _lookup_bq_cache(name: str) -> LithologyResult | None:
    if not settings.gcp_project_id or not settings.bigquery_dataset:
        return None
    try:
        from google.cloud import bigquery

        client = bigquery.Client(project=settings.gcp_project_id)
        query = f"""
            SELECT lithology, is_carbonate, confidence, source
            FROM `{settings.gcp_project_id}.{settings.bigquery_dataset}.formation_lithology`
            WHERE LOWER(formation_name) = @name
            ORDER BY updated_at DESC
            LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("name", "STRING", _key(name))
            ]
        )
        df = client.query(query, job_config=job_config).to_dataframe(
            create_bqstorage_client=False
        )
        if df.empty:
            return None
        row = df.iloc[0]
        return LithologyResult(
            lithology=row.get("lithology") or "unknown",
            is_carbonate=bool(row.get("is_carbonate", False)),
            confidence=float(row.get("confidence") or 0.0),
            source=row.get("source") or "bq_cache",
        )
    except Exception as exc:
        logger.warning("BQ lithology cache lookup failed for %s: %s", name, exc)
        return None


def _write_bq_cache(name: str, result: LithologyResult) -> None:
    if not settings.gcp_project_id or not settings.bigquery_dataset:
        return
    try:
        import datetime

        from google.cloud import bigquery

        client = bigquery.Client(project=settings.gcp_project_id)
        table_ref = (
            f"{settings.gcp_project_id}.{settings.bigquery_dataset}.formation_lithology"
        )
        rows = [
            {
                "formation_name": _key(name),
                "lithology": result.lithology,
                "is_carbonate": result.is_carbonate,
                "confidence": result.confidence,
                "source": result.source or "llm",
                "updated_at": datetime.datetime.now(datetime.UTC).isoformat(),
            }
        ]
        errors = client.insert_rows_json(table_ref, rows)
        if errors:
            logger.warning("Failed to write lithology cache for %s: %s", name, errors)
    except Exception as exc:
        logger.warning("BQ lithology cache write failed for %s: %s", name, exc)


def _llm_fallback(name: str) -> LithologyResult | None:
    """Call GenaiClient to classify an unknown formation."""
    if not settings.gcp_project_id or not settings.vertex_ai_location:
        logger.warning("LLM lithology not available: GCP project not configured")
        return None
    try:
        from google.genai import Client as GenaiClient
        from google.genai import types as genai_types

        client = GenaiClient(
            project=settings.gcp_project_id,
            location=settings.vertex_ai_location,
        )
        response = client.models.generate_content(
            model=settings.vertex_ai_model,
            contents=[LLM_PROMPT.format(formation=name)],
            config=genai_types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
            ),
        )
        text = response.text
        if not text:
            return None
        if text.startswith("```"):
            text = text.strip("`").strip()
            if text.startswith("json"):
                text = text[4:].strip()
        data = json.loads(text)
        return LithologyResult(
            lithology=data.get("lithology", "unknown"),
            is_carbonate=bool(data.get("is_carbonate", False)),
            confidence=float(data.get("confidence", 0.0)),
            source="llm",
        )
    except Exception as exc:
        logger.warning("LLM lithology fallback failed for %s: %s", name, exc)
        return None


def classify_lithology(formation_name: str) -> LithologyResult:
    """Classify a formation's lithology. Cached aggressively."""
    key = _key(formation_name)
    if not key:
        return LithologyResult(lithology="unknown", is_carbonate=False, confidence=0.0)

    if key in _cache:
        return _cache[key]

    # Layer 1: builtin
    result = _lookup_builtin(key)
    if result:
        _cache[key] = result
        return result

    # Layer 2: BQ cache
    result = _lookup_bq_cache(key)
    if result:
        _cache[key] = result
        return result

    # Layer 3: LLM fallback
    result = _llm_fallback(key)
    if result:
        _write_bq_cache(key, result)
        _cache[key] = result
        return result

    # Final fallback
    result = LithologyResult(
        lithology="unknown",
        is_carbonate=False,
        confidence=0.0,
        source="builtin_fallback",
    )
    _cache[key] = result
    return result
