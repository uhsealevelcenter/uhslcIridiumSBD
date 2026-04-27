"""
Pseudobinary-C Decoder Module

This module provides functionality to read and decode pseudobinary-c data blocks
and convert them to CSV format. It's specifically designed for pseudobinary-c
format only, distinguishing it from other pseudobinary variants (a, b, d, etc.).
"""
# pylint: disable=line-too-long,trailing-whitespace

import os
import csv
import argparse
from datetime import datetime, timedelta


class PseudobinaryCDecoder:
    """
    A simplified class for reading pseudobinary-c blocks and decoding them into CSV files.
    Contains only the essential functionality for pseudobinary-c decoding and CSV output.
    """

    def sixbit_to_decimal(self, sixbit):
        """
        Function to convert six bit characters to decimal.
        """
        # Return NaN for missing data.
        if sixbit == '///':
            return float('nan')

        # Convert each character to its ASCII value and adjust for the offset.
        double_val = [ord(ch) - 64 if ord(ch) > 63 else ord(ch) for ch in sixbit]
        # Convert each value to a binary string of length 6.
        binary_str = [format(val, '06b') for val in double_val]
        # Combine all the binary strings into one.
        combined_str = ''.join(binary_str)

        # Check if the binary number is negative (i.e., if the leftmost bit is 1).
        if combined_str[0] == '1':
            # If the number is negative, find its two's complement and flip bits.
            bin_flipped = ''.join('1' if b == '0' else '0' for b in combined_str)
            # Convert to decimal and negate.
            decimal = -(int(bin_flipped, 2) + 1)
        else:
            # If the number is positive, simply convert it to decimal.
            decimal = int(combined_str, 2)

        return decimal

    def julian_to_date(self, julian, year):
        """
        Function to convert Julian day number to date.
        """
        # Calculate the date from the provided year and julian day.
        date = datetime(year, 1, 1) + timedelta(julian - 1)
        return date.strftime('%m/%d/%Y')

    def minutes_to_time(self, minutes):
        """
        Function to convert minutes to time in HH:MM:SS format.
        """
        # Adjust for negative minutes.
        sign = "-" if minutes < 0 else ""
        # Take the absolute value for calculation.
        minutes = abs(minutes)

        # Get the time.
        hours = minutes // 60
        remaining_minutes = minutes % 60
        seconds = (remaining_minutes * 60) % 60

        return f'{sign}{hours:02d}:{remaining_minutes:02d}:{seconds:02d}'

    def convert_to_float(self, value):
        """
        Custom function to check a float value based on a threshold
        (1 million) and, if it fails, return None.
        """
        try:
            float_val = float(value)
            if abs(float_val) < 1e6:
                return float_val
            else:
                return None
        except ValueError:
            return None

    def decode_pseudobinary_c_tx(self, data, year):
        """
        Function to decode pseudobinary c data.
        """
        # Define the names of the sensors.
        sensors = ['PRS', 'RAD', 'RA2', 'RA3', 'RAS', 'ENC', 'BUB',
                           'BAT', 'SST', 'ATM', 'PSD', 'RSD', 'PR2', 'SW1',
                           'SW2', 'TST', 'TS2', 'TS3', 'TMA', 'WAV', 'WMX',
                           'WDR', 'RIN', 'AT2', 'Avail', 'Avail', 'Avail',
                           'Avail', 'Avail', 'SW1 samples', 'SW2 samples', 'PRS samples']

        # Check if the data is missing the starting "0" and prepend it if necessary.
        if data.startswith(("C1+", "C2+", "C3+", "C4+")):
            data = "0" + data

        # Initialize an empty list to store the decoded data.
        decoded_data = []
        # Ignore the first three characters (message identifier).
        data = data[3:]

        # Get the current UTC date and previous year for comparison with the tx date and modification if necessary.
        current_utc_date = datetime.utcnow()
        pyear = int(year) - 1

        # Loop over the data until it's empty or the end of message character is found.
        while len(data) > 0 and data[0] != '.':

            # Calculate the index of the sensor name.
            measurement_index = ord(data[1]) - ord('A')
            # Decode the day.
            day = self.sixbit_to_decimal(data[2:4])
            # Convert the day to date.
            date = self.julian_to_date(day, year)
            date_datetime = datetime.strptime(date, '%m/%d/%Y')

            # Update the date to the previous year if the time is in the future and it's valid on Dec 31.
            if date_datetime > current_utc_date and day >= 365:
                date = date.replace(str(year), str(pyear))

            
            # Get the sensor name.
            sensor = sensors[measurement_index]
            # Decode the start time.
            time_start = self.sixbit_to_decimal(data[4:6])
            # Decode the interval.
            interval = self.sixbit_to_decimal(data[6:8])

            # Adjust the start_time to account for truncation of seconds in the pseudo-C transmitted measurement times.
            # Subtract 1 minute from the start time.
            time_start = time_start - 1

            # Find the start of the next block.
            next_block_start = data.find('+', 8)
            # If the next block start character is not found.
            if next_block_start == -1:
                # Try to find the end of message character.
                next_block_start = data.find('.', 8)
                # If the end of message character is also not found.
                if next_block_start == -1:
                    # Use the end of the data string as the next block start.
                    next_block_start = len(data)

            # Get the measurements string.
            measurements_str = data[8:next_block_start]
            # Initialize an empty list to store the measurements.
            measurements = []
            # Loop over the measurements string in steps of 3.
            for i in range(0, len(measurements_str), 3):

                # Decode each measurement.
                measurement = self.sixbit_to_decimal(measurements_str[i:i+3])

                # Scale the measurement depending on the sensor.
                if sensor in ['PRS', 'RAD', 'RA2', 'RA3', 'RAS', 'ENC', 'BUB', 'PR2', 'TST', 'TS2', 'TS3']:
                    # Convert mm to m.
                    measurement /= 1000
                elif sensor == 'BAT':
                    # Convert to volts.
                    measurement /= 10
                elif sensor in ['ATM', 'AT2']:
                    # Convert to hPa.
                    measurement /= 10
                elif sensor == 'SST':
                    # Scale to degree C (transmitted as x10 degree C, Pseudobinary-C only).
                    measurement /= 10

                # Append the measurement to the list.
                measurements.append(measurement)

            # Loop over the measurements.
            for i, measurement in enumerate(measurements):
                # Calculate the time of each measurement.
                time = self.minutes_to_time(time_start - i * interval)
                # Only append data for sensors without 'samples' in their name.
                if 'samples' not in sensor:
                    # Append the decoded data to the list.
                    decoded_data.append({
                        'sensor': sensor,
                        'date': date,
                        'time': time,
                        'measurement': measurement
                    })

            # Move to the next block.
            data = data[next_block_start:]

        return decoded_data

    def format_data_for_csv(self, decoded_data):
        """
        Function to format decoded data for CSV output.
        """
        formatted_data = []

        for entry in decoded_data:
            # Change transmission hours and minutes to desirable format.
            time = entry['time'].split(':')
            time_hh = time[0].zfill(2)
            time_mm = time[1]
            entry['time'] = time_hh + ':' + time_mm

            # Check and modify time where necessary - hours = 24 or negative value.
            if time_hh == '24':
                date = datetime.strptime(entry['date'], '%m/%d/%Y') + timedelta(days=1)
                entry['date'] = date.strftime('%m/%d/%Y')
                entry['time'] = f'00:{time[1]}'
            if time_hh.startswith('-'):
                # Calculate the new time by subtracting the negative minutes from midnight
                # and subtracting one day.
                new_time = datetime(2000, 1, 1, 0, 0) - timedelta(minutes=int(time_mm))
                date_obj = datetime.strptime(entry['date'], '%m/%d/%Y') - timedelta(days=1)
                entry['date'] = date_obj.strftime('%m/%d/%Y')
                entry['time'] = new_time.strftime('%H:%M:%S')

            # Create timestamptz for timescaledb.
            if entry['time'].count(':') == 1:
                entry['time'] = entry['time'] + ':00'
            entry['datetime'] = datetime.strptime(entry['date'], '%m/%d/%Y').strftime('%Y-%m-%d') + ' ' + entry['time'] + '+00:00'

            # Only keep the first 3 characters of the sensor name.
            entry['sensor'] = entry['sensor'][:3]

            # Set measurement precision based on the sensor.
            if entry['sensor'] in ['SW1', 'SW2']:
                measurement_format = "{:.0f}"
            elif entry['sensor'] in ['BAT', 'ATM', 'AT2', 'SST', 'RSD']:
                measurement_format = "{:.1f}"
            else:
                measurement_format = "{:.3f}"

            # Apply measurement precision based on the sensor.
            entry['measurement'] = measurement_format.format(entry['measurement'])

            # Rename data keys to be consistent and remove those no longer needed.
            entry['time'] = entry['datetime']
            entry['data'] = entry['measurement']
            del entry['date']
            del entry['measurement']
            del entry['datetime']

            # Append to final post-processed data transmission.
            formatted_data.append(entry)

        # Note: Data will be sorted by time (oldest first) in write_to_csv
        return formatted_data

    def read_file_content(self, file_path):
        """
        Function to read the content of a file containing pseudobinary-c data.
        Returns tuple of (data, station_name) where station_name is extracted from after the first space.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read().strip()
                # Split on first space to separate pseudobinary data from station name
                parts = content.split(' ', 1)
                data = parts[0]
                if len(parts) > 1:
                    # Extract station name (first word after space, strip any trailing periods/spaces)
                    station_name = parts[1].strip().split()[0].rstrip('.')
                else:
                    station_name = None
                return data, station_name
        except (IOError, OSError) as e:
            print(f"Error reading file {file_path}: {e}")
            return None, None

    def write_to_csv(self, data, output_file, append_mode=True):
        """
        Function to write data to CSV file, loading existing data, checking for duplicates,
        and writing in time order (oldest first).
        """
        if not data:
            print("No data to write to CSV")
            return False

        # Load existing CSV data if file exists and append_mode is True
        existing_data = []
        file_exists = os.path.exists(output_file)

        if file_exists and append_mode:
            try:
                with open(output_file, 'r', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    # Skip header row
                    for row in reader:
                        existing_data.append(row)
            except (IOError, OSError) as e:
                print(f"Warning: Could not read existing CSV file {output_file}: {e}")
                existing_data = []

        # Combine existing and new data
        all_data = existing_data + data

        # Deduplicate based on (time, sensor) combination
        # Use a set to track seen combinations, keeping the first occurrence
        seen = set()
        deduplicated_data = []
        duplicates_found = 0

        for row in all_data:
            # Create a unique key from time and sensor
            key = (row['time'], row['sensor'])
            if key not in seen:
                seen.add(key)
                deduplicated_data.append(row)
            else:
                duplicates_found += 1

        if duplicates_found > 0:
            print(f"Found and removed {duplicates_found} duplicate record(s)")

        # Sort by time (oldest first)
        try:
            deduplicated_data = sorted(
                deduplicated_data,
                key=lambda x: datetime.strptime(x['time'], '%Y-%m-%d %H:%M:%S+00:00')
            )
        except (ValueError, KeyError) as e:
            print(f"Warning: Could not sort by time: {e}. Writing unsorted data.")
            # Fallback: try string sort
            deduplicated_data = sorted(deduplicated_data, key=lambda x: x.get('time', ''))

        # Write all data to CSV (overwrite mode to ensure clean file)
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['time', 'sensor', 'data']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                # Write all deduplicated and sorted data
                for row in deduplicated_data:
                    writer.writerow(row)

            new_records = len(data)
            total_records = len(deduplicated_data)
            print(f"Successfully wrote {total_records} total records ({new_records} new) to {output_file}")
            return True

        except (IOError, OSError) as e:
            print(f"Error writing to CSV file {output_file}: {e}")
            return False

    def process_pseudobinary_file(self, input_file, output_file, year, append_mode=True):
        """
        Main function to process a pseudobinary-c file and write to CSV.

        Args:
            input_file (str): Path to the input file containing pseudobinary-c data
            output_file (str): Path to the output CSV file
            year (int): Year for the data
            append_mode (bool): Whether to append to existing CSV file (default: True)

        Returns:
            tuple: (bool, str) - (True if successful, station_name) or (False, None)
        """
        # Read the file content
        data, station_name = self.read_file_content(input_file)
        if data is None:
            return False, None

        # Decode the pseudobinary data
        decoded_data = self.decode_pseudobinary_c_tx(data, year)
        if not decoded_data:
            print("No data decoded from pseudobinary file")
            return False, station_name

        # Format the data for CSV
        formatted_data = self.format_data_for_csv(decoded_data)
        if not formatted_data:
            print("No formatted data to write")
            return False, station_name

        # Write to CSV
        success = self.write_to_csv(formatted_data, output_file, append_mode)
        return success, station_name


def main():
    """
    Example usage of the PseudobinaryCDecoder class.
    """
    parser = argparse.ArgumentParser(description='Decode pseudobinary-c data files to CSV')
    parser.add_argument('-i', '--input', required=True, help='Input file containing pseudobinary-c data')
    parser.add_argument('-o', '--output', default='decoded_data.csv', help='Output CSV file (default: decoded_data.csv)')
    parser.add_argument('-y', '--year', type=int, default=2024, help='Year for the data (default: 2024)')
    parser.add_argument('--no-append', action='store_false', dest='append_mode', help='Overwrite output file instead of appending')

    args = parser.parse_args()

    decoder = PseudobinaryCDecoder()

    # Process the file
    success, station_name = decoder.process_pseudobinary_file(args.input, args.output, args.year, args.append_mode)

    if success:
        if station_name:
            print(f"Processing completed successfully! Station: {station_name}")
        else:
            print("Processing completed successfully!")
    else:
        print("Processing failed!")


if __name__ == "__main__":
    main()
