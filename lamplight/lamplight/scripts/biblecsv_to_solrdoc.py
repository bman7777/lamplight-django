#!/usr/bin/env python3
import argparse
import csv
import json
import re
import sys


def remove_markup_tags(text):
    # This pattern matches any tag structure like <...>
    clean_text = re.sub(r"<[^>]+>", "", text)
    clean_text = re.sub(r"\[[^\]]*\]", "", clean_text)
    return clean_text


def csv_to_json(csv_file_path, json_file_path=None, encoding="utf-8"):
    """
    Convert a CSV file to JSON format

    Args:
        csv_file_path (str): Path to the input CSV file
        json_file_path (str, optional): Path for the output JSON file. If None, prints to stdout.
        encoding (str, optional): File encoding. Defaults to 'utf-8'.

    Returns:
        bool: True if conversion was successful, False otherwise
    """
    try:
        # Read the CSV file
        with open(csv_file_path, "r", encoding=encoding) as csv_file:
            csv_reader = csv.reader(csv_file, escapechar="\\")

            output = []
            for col in csv_reader:
                output.append(
                    {
                        "id": f"nasb95:{col[0]}:{col[1]}:{col[2]}",
                        "_text_": remove_markup_tags(col[3]),
                    }
                )

            # Convert to JSON
            if json_file_path:
                # Write to a file
                with open(json_file_path, "w", encoding=encoding) as json_file:
                    json.dump(output, json_file, ensure_ascii=False, indent=4)
                print(f"Conversion successful. JSON saved to {json_file_path}")
            else:
                # Print to stdout
                print(json.dumps(output, indent=4))

            return True
    except Exception as e:
        print(f"Error converting CSV to JSON: {str(e)}", file=sys.stderr)
        return False


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Convert CSV file to JSON")
    parser.add_argument("csv_file", help="Path to the input CSV file")
    parser.add_argument(
        "-o",
        "--output",
        help="Path for the output JSON file (if not provided, prints to stdout)",
    )
    parser.add_argument(
        "-e", "--encoding", default="utf-8", help="File encoding (default: utf-8)"
    )

    # Parse arguments
    args = parser.parse_args()

    # Perform the conversion
    csv_to_json(args.csv_file, args.output, args.encoding)


if __name__ == "__main__":
    main()
