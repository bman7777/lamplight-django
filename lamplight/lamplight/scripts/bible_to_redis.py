import argparse
import csv
import os.path

import redis
from dotenv import load_dotenv


def csv_to_redis_hash(csv_file, hash_prefix="nasb95"):
    """
    Read data from a CSV file and insert each row as a Redis hash.

    Args:
        csv_file (str): Path to the CSV file
        hash_prefix (str): Prefix for Redis hash keys
    """
    # Validate the CSV file exists
    if not os.path.isfile(csv_file):
        raise FileNotFoundError(f"CSV file not found: {csv_file}")

    # Connect to Redis
    r = redis.Redis(
        host="localhost",
        port=6379,
        db=0,
        password=os.getenv("REDIS_PASS"),
        decode_responses=True,  # Automatically decode responses to strings
    )

    # Check connection
    try:
        r.ping()
        print(f"Connected to Redis at localhost:6379")
    except redis.ConnectionError as e:
        print(f"Failed to connect to Redis: {e}")
        return

    # Set up a custom dialect that preserves escaped characters (otherwise we will lose all commas)
    csv.register_dialect(
        "escaped", escapechar="\\", doublequote=False, quoting=csv.QUOTE_MINIMAL
    )

    book_map = [
        {"genesis": "gen"},
        {"exodus": "exo"},
        {"leviticus": "lev"},
        {"numbers": "num"},
        {"deuteronomy": "deu"},
        {"joshua": "jos"},
        {"judges": "jdg"},
        {"ruth": "rth"},
        {"1 samuel": "1sa"},
        {"2 samuel": "2sa"},
        {"1 kings": "1ki"},
        {"2 kings": "2ki"},
        {"1 chronicles": "1ch"},
        {"2 chronicles": "2ch"},
        {"ezra": "ezr"},
        {"nehemiah": "neh"},
        {"esther": "est"},
        {"job": "job"},
        {"psalms": "psa"},
        {"proverbs": "pro"},
        {"ecclesiastes": "ecc"},
        {"song of songs": "sng"},
        {"isaiah": "isa"},
        {"jeremiah": "jer"},
        {"lamentations": "lam"},
        {"ezekiel": "eze"},
        {"daniel": "dan"},
        {"hosea": "hos"},
        {"joel": "joe"},
        {"amos": "amo"},
        {"obadiah": "oba"},
        {"jonah": "jon"},
        {"micah": "mic"},
        {"nahum": "nah"},
        {"habakkuk": "hab"},
        {"zephaniah": "zep"},
        {"haggai": "hag"},
        {"zechariah": "zec"},
        {"malachi": "mal"},
        {"matthew": "mat"},
        {"mark": "mar"},
        {"luke": "luk"},
        {"john": "jhn"},
        {"acts": "act"},
        {"romans": "rom"},
        {"1 corinthians": "1co"},
        {"2 corinthians": "2co"},
        {"galatians": "gal"},
        {"ephesians": "eph"},
        {"philippians": "phl"},
        {"colossians": "col"},
        {"1 thessalonians": "1th"},
        {"2 thessalonians": "2th"},
        {"1 timothy": "1ti"},
        {"2 timothy": "2ti"},
        {"titus": "tit"},
        {"philemon": "phm"},
        {"hebrews": "heb"},
        {"james": "jas"},
        {"1 peter": "1pe"},
        {"2 peter": "2pe"},
        {"1 john": "1jo"},
        {"2 john": "2jo"},
        {"3 john": "3jo"},
        {"jude": "jde"},
        {"revelation": "rev"},
    ]

    # Open and process the CSV file
    with open(csv_file, "r", newline="", encoding="utf-8") as file:
        reader = csv.reader(file, dialect="escaped")

        # Process data rows
        row_count = 0
        for row in reader:
            if not row:  # Skip empty rows
                continue

            try:
                text = "" if len(row) <= 3 else row[3]
                display_name = ""

                if row[1] == row[2] == "1":
                    for book in book_map:
                        if list(book.values())[0] == row[0]:
                            display_name = list(book.keys())[0]
                            print(f"adding key for: {hash_prefix}:{row[0]}")
                            r.hset(
                                f"{hash_prefix}:{row[0]}",
                                mapping={"name": row[0], "data": display_name},
                            )
                            break

                if row[2] == "1":
                    r.hset(
                        f"{hash_prefix}:{row[0]}:{row[1]}",
                        mapping={
                            "name": f"{row[0]} {row[1]}",
                            "data": f"{display_name} chapter {row[1]}",
                        },
                    )

                r.hset(
                    f"{hash_prefix}:{row[0]}:{row[1]}:{row[2]}",
                    mapping={"name": f"{row[0]} {row[1]}:{row[2]}", "data": text},
                )
                row_count += 1

                if row_count % 1000 == 0:
                    print(f"Processed {row_count} rows...")

            except Exception as e:
                print(f"Error processing row {row_count+1}: {e}")
                print(f"Row data: {row}")

        print(f"Import complete. Processed {row_count} rows.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import CSV data to Redis hashes")
    parser.add_argument("csv_file", help="Path to the CSV file to import")
    parser.add_argument("--prefix", default="nasb95", help="Prefix for Redis hash keys")

    args = parser.parse_args()
    load_dotenv()

    try:
        csv_to_redis_hash(args.csv_file, hash_prefix=args.prefix)
    except Exception as e:
        print(f"Error: {e}")
