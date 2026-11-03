"""Raw data ingestion and immutable provenance tracking module.

Saves untouched raw downloads into data/raw/ alongside an immutable
metadata.json describing the data source, station, access timestamp,
and SHA-256 integrity checksum.
"""

from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union
import pandas as pd


def compute_sha256(file_path: Union[str, Path]) -> str:
    """Compute SHA-256 hash of a file for integrity provenance."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()


def ingest_raw_csv(
    source_file: Union[str, Path],
    station_name: str,
    city: str = "Bengaluru",
    source_description: str = "CPCB National AQI Portal",
    target_raw_dir: Union[str, Path] = "data/raw",
) -> Dict[str, Any]:
    """Ingest a raw CSV file into the immutable raw/ directory with metadata.json.

    Args:
        source_file: Path to source CSV.
        station_name: Exact station name (e.g. 'BTM Layout, Bengaluru - CPCB').
        city: City name.
        source_description: Official source text.
        target_raw_dir: Target raw storage folder.

    Returns:
        Metadata dictionary.
    """
    src = Path(source_file)
    if not src.exists():
        raise FileNotFoundError(f"Source file does not exist: {src}")

    target_dir = Path(target_raw_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    dest_file = target_dir / src.name

    # Copy raw content untouched
    content = src.read_bytes()
    dest_file.write_bytes(content)

    checksum = compute_sha256(dest_file)

    # Read basic properties without modifying
    df = pd.read_csv(dest_file)
    row_count = len(df)

    date_col = None
    for col in df.columns:
        if "date" in col.lower():
            date_col = col
            break

    date_range = "Unknown"
    if date_col:
        try:
            dates = pd.to_datetime(df[date_col]).dropna()
            date_range = f"{dates.min().strftime('%Y-%m-%d')} to {dates.max().strftime('%Y-%m-%d')}"
        except Exception:
            pass

    metadata = {
        "station": station_name,
        "city": city,
        "source": source_description,
        "raw_filename": dest_file.name,
        "ingestion_timestamp": datetime.now().isoformat(),
        "sha256_checksum": checksum,
        "row_count": row_count,
        "date_range": date_range,
        "columns": list(df.columns),
    }

    meta_path = target_dir / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return metadata

