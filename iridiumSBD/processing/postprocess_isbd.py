#!/usr/bin/env python3
"""Post-process saved Iridium DirectIP ``.isbd`` files.

The DirectIP listener saves the full binary DirectIP envelope to ``data/inbox``.
This module extracts the MO payload from that envelope, optionally writes a raw
payload copy, decodes UHSLC pseudobinary-C payload text to CSV, and files the
original message into archive/empty/error directories.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from iridiumSBD import IridiumSBD, valid_isbd
from iridiumSBD.decode.pseudobinary_c_decoder import PseudobinaryCDecoder

LOGGER = logging.getLogger(__name__)


class PostProcessError(RuntimeError):
    """Raised when an ISBD message cannot be post-processed."""


def _safe_name(value: str, default: str = "unknown") -> str:
    """Return a conservative filename-safe token."""
    value = (value or "").strip()
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    value = value.strip("._-")
    return value or default


def _unique_path(path: Path) -> Path:
    """Return ``path`` or a numbered variant if the path already exists."""
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _move_file(src: Path, dest_dir: Path) -> Path:
    """Move ``src`` into ``dest_dir`` without overwriting existing files."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = _unique_path(dest_dir / src.name)
    shutil.move(str(src), str(dest))
    return dest


def infer_data_dir(input_file: Path) -> Path:
    """Infer the runtime data directory from an input file path."""
    parent = input_file.resolve().parent
    if parent.name in {"inbox", "raw", "corrupted", "archive", "empty", "error"}:
        return parent.parent
    return parent


def archive_day(input_file: Path) -> str:
    """Derive an archive day from the listener filename, falling back to today."""
    match = re.match(r"^(\d{8})", input_file.name)
    if match:
        return match.group(1)
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def parse_payload_text(payload: bytes) -> Tuple[str, Optional[str]]:
    """Decode a payload as text and extract ``(pseudobinary, station_name)``.

    Operational UHSLC payloads are expected to look like::

        <pseudobinary-c-message> <station-name>

    The station token is optional; if absent, callers can fall back to IMEI.
    """
    try:
        content = payload.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise PostProcessError("Payload is not valid UTF-8 text") from exc

    if not content:
        raise PostProcessError("Payload is empty")

    parts = content.split(" ", 1)
    data = parts[0].strip()
    station_name = None
    if len(parts) > 1:
        station_name = parts[1].strip().split()[0].rstrip(".") or None

    if not data:
        raise PostProcessError("No pseudobinary-C data found in payload")
    return data, station_name


def write_raw_payload(payload: bytes, raw_dir: Path, input_file: Path, imei: str) -> Path:
    """Write the extracted MO payload to the raw payload directory."""
    day = archive_day(input_file)
    raw_day_dir = raw_dir / day
    raw_day_dir.mkdir(parents=True, exist_ok=True)
    timestamp = input_file.name[:14] if re.match(r"^\d{14}", input_file.name) else datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    output = _unique_path(raw_day_dir / f"{timestamp}-{_safe_name(imei)}.raw")
    output.write_bytes(payload)
    return output


def decode_payload_to_csv(payload_text: str, station_name: str, output_dir: Path, year: int) -> Path:
    """Decode pseudobinary-C payload text and append it to a station/year CSV."""
    decoder = PseudobinaryCDecoder()
    decoded = decoder.decode_pseudobinary_c_tx(payload_text, year)
    if not decoded:
        raise PostProcessError("No records decoded from pseudobinary-C payload")

    formatted = decoder.format_data_for_csv(decoded)
    if not formatted:
        raise PostProcessError("Decoded payload produced no formatted CSV rows")

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{_safe_name(station_name)}_{year}.csv"
    if not decoder.write_to_csv(formatted, str(csv_path), append_mode=True):
        raise PostProcessError(f"Failed to write decoded CSV: {csv_path}")
    return csv_path


def process_isbd(
    input_file: Path,
    data_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    raw_dir: Optional[Path] = None,
    archive_dir: Optional[Path] = None,
    empty_dir: Optional[Path] = None,
    error_dir: Optional[Path] = None,
    year: Optional[int] = None,
    archive: bool = True,
    write_raw: bool = True,
    decode: bool = True,
) -> Tuple[Optional[Path], Optional[Path]]:
    """Process one saved DirectIP ``.isbd`` file.

    Returns:
        ``(raw_payload_path, csv_path)``. Either value may be ``None`` depending
        on options and message contents.
    """
    input_file = Path(input_file).resolve()
    if data_dir is None:
        data_dir = infer_data_dir(input_file)
    data_dir = Path(data_dir).resolve()

    output_dir = Path(output_dir).resolve() if output_dir else data_dir / "csv"
    raw_dir = Path(raw_dir).resolve() if raw_dir else data_dir / "raw"
    archive_dir = Path(archive_dir).resolve() if archive_dir else data_dir / "archive"
    empty_dir = Path(empty_dir).resolve() if empty_dir else data_dir / "empty"
    error_dir = Path(error_dir).resolve() if error_dir else data_dir / "error"
    year = int(year or datetime.now(timezone.utc).year)

    if not input_file.exists():
        raise PostProcessError(f"Input file does not exist: {input_file}")

    try:
        message = input_file.read_bytes()
        if not valid_isbd(message):
            raise PostProcessError("Input file is not a complete valid DirectIP ISBD message")

        isbd = IridiumSBD(message)
        if not hasattr(isbd, "payload"):
            LOGGER.info("No MO payload found; moving to empty directory: %s", input_file)
            if archive:
                _move_file(input_file, empty_dir)
            return None, None

        imei = isbd.attributes.get("header", {}).get("IMEI", "unknown")
        payload = isbd.payload["data"]

        raw_path = write_raw_payload(payload, raw_dir, input_file, imei) if write_raw else None
        csv_path = None

        if decode:
            payload_text, station_name = parse_payload_text(payload)
            csv_station = station_name or imei
            csv_path = decode_payload_to_csv(payload_text, csv_station, output_dir, year)
            LOGGER.info("Decoded %s to %s", input_file, csv_path)

        if archive:
            day_dir = archive_dir / archive_day(input_file)
            archived = _move_file(input_file, day_dir)
            LOGGER.info("Archived ISBD file to %s", archived)

        return raw_path, csv_path

    except Exception as exc:  # noqa: BLE001 - command-line tool should file failures consistently
        LOGGER.error("Failed to process %s: %s", input_file, exc, exc_info=True)
        if archive and input_file.exists():
            _move_file(input_file, error_dir)
        if isinstance(exc, PostProcessError):
            raise
        raise PostProcessError(str(exc)) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract and optionally decode the MO payload from a saved Iridium DirectIP .isbd file."
    )
    parser.add_argument("input", help="Saved DirectIP .isbd file, normally from data/inbox")
    parser.add_argument("--data-dir", help="Runtime data directory. Default: inferred from input path")
    parser.add_argument("--output-dir", help="Directory for decoded station/year CSV files. Default: <data-dir>/csv")
    parser.add_argument("--raw-dir", help="Directory for extracted raw payload files. Default: <data-dir>/raw")
    parser.add_argument("--archive-dir", help="Directory for processed .isbd files. Default: <data-dir>/archive")
    parser.add_argument("--empty-dir", help="Directory for .isbd files without payloads. Default: <data-dir>/empty")
    parser.add_argument("--error-dir", help="Directory for failed .isbd files. Default: <data-dir>/error")
    parser.add_argument("--year", type=int, help="Year used for Julian-day conversion. Default: current UTC year")
    parser.add_argument("--no-archive", action="store_true", help="Leave the input .isbd file in place")
    parser.add_argument("--no-raw", action="store_true", help="Do not write an extracted raw payload copy")
    parser.add_argument("--raw-only", action="store_true", help="Extract the raw payload but skip pseudobinary-C decoding")
    parser.add_argument("--loglevel", default="info", choices=["debug", "info", "warning", "error"])
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.loglevel.upper()),
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    try:
        raw_path, csv_path = process_isbd(
            input_file=Path(args.input),
            data_dir=Path(args.data_dir) if args.data_dir else None,
            output_dir=Path(args.output_dir) if args.output_dir else None,
            raw_dir=Path(args.raw_dir) if args.raw_dir else None,
            archive_dir=Path(args.archive_dir) if args.archive_dir else None,
            empty_dir=Path(args.empty_dir) if args.empty_dir else None,
            error_dir=Path(args.error_dir) if args.error_dir else None,
            year=args.year,
            archive=not args.no_archive,
            write_raw=not args.no_raw,
            decode=not args.raw_only,
        )
    except PostProcessError:
        return 1

    if raw_path:
        LOGGER.info("Raw payload: %s", raw_path)
    if csv_path:
        LOGGER.info("Decoded CSV: %s", csv_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
