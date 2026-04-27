#!/usr/bin/env python3
"""
Decode pseudobinary-c data files to CSV with automatic station name detection.

This script reads pseudobinary-c data files, extracts the station name,
creates CSV files named after the station and current year, and archives
the processed input files.
"""
# pylint: disable=line-too-long,trailing-whitespace


import argparse
import os
import shutil
import sys
import logging
from datetime import datetime, timezone
from pseudobinary_c_decoder import PseudobinaryCDecoder

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def archive_file(filepath, station_name=None, archive_base_dir=None):
    """
    Archive a processed file to the archive directory structure.
    
    Args:
        filepath (str): Path to the file to archive
        station_name (str): Optional station name for the archive filename
        archive_base_dir (str): Base directory for archives (default: same dir as file)
    """
    try:
        if not os.path.exists(filepath):
            logger.warning("File not found for archiving: %s", filepath)
            return False
        
        # Determine archive base directory
        if archive_base_dir is None:
            # If file is in inbox, go up to data directory, otherwise use file's directory
            file_dir = os.path.dirname(os.path.abspath(filepath))
            if 'inbox' in file_dir:
                archive_base_dir = os.path.dirname(file_dir)  # Go up from inbox to data
            else:
                archive_base_dir = file_dir
        
        # Create archive directory structure by date
        timestamp = datetime.now(timezone.utc)
        day_dir = timestamp.strftime('%Y%m%d')
        archive_dir = os.path.join(archive_base_dir, 'archive', day_dir)
        os.makedirs(archive_dir, exist_ok=True)
        
        # Create processed filename with additional info
        filename = os.path.basename(filepath)
        base_name = os.path.splitext(filename)[0]
        extension = os.path.splitext(filename)[1] or '.raw'
        
        # Add station name to archive filename if available
        if station_name:
            processed_name = f"{base_name}_{station_name}{extension}"
        else:
            processed_name = filename
        
        # Move to archive
        archive_path = os.path.join(archive_dir, processed_name)
        shutil.move(filepath, archive_path)
        
        logger.info("Archived: %s -> %s", filename, archive_path)
        return True
        
    except (OSError, shutil.Error) as e:
        logger.error("Error archiving file %s: %s", filepath, e)
        return False


def move_to_error(filepath, error_base_dir=None):
    """
    Move a file to the error directory.
    
    Args:
        filepath (str): Path to the file to move
        error_base_dir (str): Base directory for errors (default: same dir as file)
    """
    try:
        if not os.path.exists(filepath):
            return False
        
        # Determine error base directory
        if error_base_dir is None:
            file_dir = os.path.dirname(os.path.abspath(filepath))
            if 'inbox' in file_dir:
                error_base_dir = os.path.dirname(file_dir)  # Go up from inbox to data
            else:
                error_base_dir = file_dir
        
        error_dir = os.path.join(error_base_dir, 'error')
        os.makedirs(error_dir, exist_ok=True)
        shutil.move(filepath, error_dir)
        logger.info("Moved to error directory: %s", filepath)
        return True
    except (OSError, shutil.Error) as e:
        logger.error("Error moving file to error directory: %s", e)
        return False


def main():
    """
    Main function to decode pseudobinary-c files with automatic CSV naming and archiving.
    """
    parser = argparse.ArgumentParser(description='Decode pseudobinary-c data files to CSV')
    parser.add_argument('input', help='Input file containing pseudobinary-c data')
    parser.add_argument('--archive-dir', help='Base directory for archives (default: auto-detect)')
    parser.add_argument('--no-archive', action='store_true', help='Skip archiving the input file')

    args = parser.parse_args()

    # Validate input file exists
    if not os.path.exists(args.input):
        logger.error("Input file not found: %s", args.input)
        sys.exit(1)

    # Check if file is empty
    try:
        if os.path.getsize(args.input) == 0:
            logger.warning("Empty input file: %s", args.input)
            # Move empty files to empty directory
            file_dir = os.path.dirname(os.path.abspath(args.input))
            if 'inbox' in file_dir:
                data_dir = os.path.dirname(file_dir)
            else:
                data_dir = file_dir
            empty_dir = os.path.join(data_dir, 'empty')
            os.makedirs(empty_dir, exist_ok=True)
            shutil.move(args.input, empty_dir)
            logger.info("Moved empty file to: %s", empty_dir)
            sys.exit(0)
    except OSError as e:
        logger.error("Error checking file size: %s", e)
        move_to_error(args.input, args.archive_dir)
        sys.exit(1)

    try:
        # Get current year
        current_year = datetime.now().year

        # Create decoder instance
        decoder = PseudobinaryCDecoder()

        # Read file to extract station name
        data, station_name = decoder.read_file_content(args.input)
        if data is None:
            logger.error("Could not read input file")
            move_to_error(args.input, args.archive_dir)
            sys.exit(1)

        # Generate output filename
        if station_name:
            output_file = f"{station_name}_{current_year}.csv"
            logger.info("Station detected: %s", station_name)
        else:
            output_file = f"decoded_data_{current_year}.csv"
            logger.warning("No station name found, using default filename")

        # Decode the pseudobinary data
        decoded_data = decoder.decode_pseudobinary_c_tx(data, current_year)
        if not decoded_data:
            logger.warning("No data decoded from pseudobinary file")
            move_to_error(args.input, args.archive_dir)
            sys.exit(1)

        # Format the data for CSV
        formatted_data = decoder.format_data_for_csv(decoded_data)
        if not formatted_data:
            logger.warning("No formatted data to write")
            move_to_error(args.input, args.archive_dir)
            sys.exit(1)

        # Write to CSV
        success = decoder.write_to_csv(formatted_data, output_file, append_mode=True)

        if success:
            logger.info("Successfully created/updated %s", output_file)
            
            # Archive the input file if not disabled
            if not args.no_archive:
                archive_file(args.input, station_name, args.archive_dir)
            else:
                logger.info("Archiving skipped (--no-archive flag set)")
            
            logger.info("Processing completed successfully")
        else:
            logger.error("Failed to write CSV file")
            move_to_error(args.input, args.archive_dir)
            sys.exit(1)

    except (OSError, ValueError, KeyError) as e:
        logger.error("Error processing %s: %s", args.input, e, exc_info=True)
        move_to_error(args.input, args.archive_dir)
        sys.exit(1)


if __name__ == "__main__":
    main()

