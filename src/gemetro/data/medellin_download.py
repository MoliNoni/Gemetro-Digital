"""I-04: reproducible download of the public Medellín sources.

Sources (DATA_SOURCES.md S-03, S-04, S-15; PHASE_2_IMPLEMENTATION.md L-11):
- Afluencia 2025 (Metro de Medellín, ArcGIS item of type "Document Link").
- GTFS 2025 (Metro de Medellín, ArcGIS item).
- IDEAM air temperature (sbwg-7ju4) and air humidity (uext-mhny), station 0027015330
  (Olaya Herrera), GPRS sensors only (0071 temperature, 0028 humidity), local year 2025.

Files land in data/raw/medellin/ (never versioned). data/manifests/medellin.json records
where each file came from and its SHA-256. A file already on disk whose hash matches the
manifest is not downloaded again.

The pressure p = 851 hPa is a closed constant and is not downloaded.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import urllib.parse
import urllib.request

from gemetro.manifest import sha256_of, write_manifest
from gemetro.paths import DATA_RAW, MANIFESTS, REPO_ROOT

MEDELLIN_RAW = DATA_RAW / "medellin"
MANIFEST_PATH = MANIFESTS / "medellin.json"

ARCGIS_ITEM = "https://www.arcgis.com/sharing/rest/content/items/{item}"
SOCRATA_RESOURCE = "https://www.datos.gov.co/resource/{dataset}.csv"
SOCRATA_PAGE_SIZE = 50_000

IDEAM_STATION = "0027015330"
# Local year 2025 (UTC-5, no daylight saving) expressed in UTC, the timezone of the data.
IDEAM_UTC_START = "2025-01-01T05:00:00"
IDEAM_UTC_END = "2026-01-01T04:59:59.999"

ARCGIS_SOURCES = {
    "afluencia_2025.xlsx": {"source": "S-03", "item": "d6bb62fc46db490db6f8783736969d15"},
    "gtfs_2025.zip": {"source": "S-15", "item": "929fbd2dbfbf493ab44935577e8fbff6"},
}

IDEAM_SOURCES = {
    "ideam_temperature_0071_2025.csv": {"dataset": "sbwg-7ju4", "sensor": "0071"},
    "ideam_humidity_0028_2025.csv": {"dataset": "uext-mhny", "sensor": "0028"},
}


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "gemetro-pipeline"})
    with urllib.request.urlopen(request, timeout=300) as response:
        return response.read()


def _arcgis_data_url(item: str) -> str:
    """Resolve the downloadable URL of an ArcGIS item.

    A "Document Link" item points to another URL; any other item serves its own data.
    """
    meta = json.loads(_get(ARCGIS_ITEM.format(item=item) + "?f=json"))
    if meta.get("type") == "Document Link":
        return meta["url"]
    return ARCGIS_ITEM.format(item=item) + "/data"


def ideam_query(dataset: str, sensor: str) -> dict[str, str]:
    """Socrata query parameters for one IDEAM sensor over the local year 2025."""
    return {
        "$select": "fechaobservacion,valorobservado,codigosensor",
        "$where": (
            f"codigoestacion='{IDEAM_STATION}' AND codigosensor='{sensor}' AND "
            f"fechaobservacion between '{IDEAM_UTC_START}' and '{IDEAM_UTC_END}'"
        ),
        "$order": "fechaobservacion,:id",
    }


def _download_ideam(dataset: str, sensor: str) -> tuple[bytes, str, dict[str, str]]:
    url = SOCRATA_RESOURCE.format(dataset=dataset)
    params = ideam_query(dataset, sensor)
    header: bytes | None = None
    body: list[bytes] = []
    offset = 0
    while True:
        page_params = {**params, "$limit": str(SOCRATA_PAGE_SIZE), "$offset": str(offset)}
        page = _get(url + "?" + urllib.parse.urlencode(page_params))
        lines = page.splitlines(keepends=True)
        if header is None:
            header = lines[0]
        rows = lines[1:]
        body.extend(rows)
        if len(rows) < SOCRATA_PAGE_SIZE:
            break
        offset += SOCRATA_PAGE_SIZE
    assert header is not None
    return header + b"".join(body), url, params


def _load_manifest() -> dict:
    if MANIFEST_PATH.is_file():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {"root": MEDELLIN_RAW.relative_to(REPO_ROOT).as_posix(), "files": [], "sources": {}}


def _is_current(manifest: dict, name: str) -> bool:
    path = MEDELLIN_RAW / name
    entry = next((f for f in manifest["files"] if f["path"] == name), None)
    return entry is not None and path.is_file() and sha256_of(path) == entry["sha256"]


def download_all(force: bool = False) -> dict:
    """Download every Medellín source that is missing or stale and rewrite the manifest."""
    MEDELLIN_RAW.mkdir(parents=True, exist_ok=True)
    manifest = _load_manifest()
    files = {f["path"]: f for f in manifest["files"]}
    sources = dict(manifest.get("sources", {}))
    today = dt.datetime.now(tz=dt.UTC).date().isoformat()

    for name, spec in {**ARCGIS_SOURCES, **IDEAM_SOURCES}.items():
        if not force and _is_current(manifest, name):
            print(f"up to date: {name}")
            continue
        if name in ARCGIS_SOURCES:
            url = _arcgis_data_url(spec["item"])
            content = _get(url)
            origin = {"source": spec["source"], "arcgis_item": spec["item"], "url": url}
        else:
            content, url, params = _download_ideam(spec["dataset"], spec["sensor"])
            origin = {"source": "S-04", "dataset": spec["dataset"], "sensor": spec["sensor"],
                      "url": url, "params": params}
        path = MEDELLIN_RAW / name
        path.write_bytes(content)
        files[name] = {"path": name, "size": len(content), "sha256": sha256_of(path)}
        sources[name] = {**origin, "retrieved": today}
        print(f"downloaded: {name} ({len(content)} bytes)")

    manifest = {
        "root": MEDELLIN_RAW.relative_to(REPO_ROOT).as_posix(),
        "files": [files[k] for k in sorted(files)],
        "sources": {k: sources[k] for k in sorted(sources)},
    }
    write_manifest(manifest, MANIFEST_PATH)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m gemetro.data.medellin_download")
    parser.add_argument("--force", action="store_true", help="download even if up to date")
    download_all(force=parser.parse_args().force)


if __name__ == "__main__":
    main()
