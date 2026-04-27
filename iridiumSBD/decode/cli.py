#!/usr/bin/env python3
"""CLI for decoding already-extracted UHSLC pseudobinary-C payload text."""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from iridiumSBD.processing.postprocess_isbd import _safe_name, _move_file
from iridiumSBD.decode.pseudobinary_c_decoder import PseudobinaryCDecoder

LOGGER = logging.getLogger(__name__)


def _read_payload_file(path: Path) -> tuple[str, Optional[str]]:
    decoder = PseudobinaryCDecoder()
    return decoder.read_file_content(str(path))


def decode_file(input_file: Path, output_dir: Path, year: int, archive_dir: Optional[Path] = None) -> Path:
    decoder = PseudobinaryCDecoder()
    data, station_name = _read_payload_file(input_file)
    if data is None:
        raise RuntimeError(f"Could not read input file: {input_file}")

    decoded = decoder.decode_pseudobinary_c_tx(data, year)
    if not decoded:
        raise RuntimeError("No records decoded from pseudobinary-C file")

    formatted = decoder.format_data_for_csv(decoded)
    if not formatted:
        raise RuntimeError("Decoded file produced no formatted CSV rows")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{_safe_name(station_name, 'decoded_data')}_{year}.csv"
    if not decoder.write_to_csv(formatted, str(output_file), append_mode=True):
        raise RuntimeError(f"Failed to write {output_file}")

    if archive_dir is not None:
        day = datetime.now(timezone.utc).strftime("%Y%m%d")
        _move_file(input_file, archive_dir / day)

    return output_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Decode an already-extracted pseudobinary-C payload text file to CSV.")
    parser.add_argument("input", help="Text file containing pseudobinary-C payload data")
    parser.add_argument("--output-dir", default=".", help="Directory for decoded CSV output. Default: current directory")
    parser.add_argument("--year", type=int, default=datetime.now(timezone.utc).year, help="Year for Julian-day conversion")
    parser.add_argument("--archive-dir", help="Optional archive directory for processed input files")
    parser.add_argument("--error-dir", help="Optional error directory for failed input files")
    parser.add_argument("--loglevel", default="info", choices=["debug", "info", "warning", "error"])
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.loglevel.upper()), format="%(asctime)s - %(levelname)s - %(message)s")

    input_file = Path(args.input).resolve()
    try:
        if input_file.stat().st_size == 0:
            raise RuntimeError("Input file is empty")
        output_file = decode_file(
            input_file=input_file,
            output_dir=Path(args.output_dir).resolve(),
            year=args.year,
            archive_dir=Path(args.archive_dir).resolve() if args.archive_dir else None,
        )
        LOGGER.info("Decoded CSV: %s", output_file)
        return 0
    except Exception as exc:  # noqa: BLE001 - command-line tool should return a non-zero status
        LOGGER.error("Failed to decode %s: %s", input_file, exc, exc_info=True)
        if args.error_dir and input_file.exists():
            error_dir = Path(args.error_dir).resolve()
            error_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(input_file), str(error_dir / input_file.name))
        return 1


if __name__ == "__main__":
    sys.exit(main())
