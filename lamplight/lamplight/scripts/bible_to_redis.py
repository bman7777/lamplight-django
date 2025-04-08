"""Import all the verses from a csv into a redis connection for future quick access."""

import argparse
import csv
import json
import os.path

import redis
from dotenv import load_dotenv


def redis_conn():
    """Connect to Redis"""
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
        print("Connected to Redis at localhost:6379")
    except redis.ConnectionError as e:
        print(f"Failed to connect to Redis: {e}")

    return r


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

    r = redis_conn()

    # Set up a custom dialect that preserves escaped characters (otherwise we will lose all commas)
    csv.register_dialect(
        "escaped", escapechar="\\", doublequote=False, quoting=csv.QUOTE_MINIMAL
    )

    with open("book_map.json", "r", encoding="utf-8") as f:
        book_map = json.load(f)

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

            except Exception as e:  # pragma pylint: disable=broad-exception-caught
                print(f"Error processing row {row_count+1}: {e}")
                print(f"Row data: {row}")

        print(f"Import complete. Processed {row_count} rows.")


def versioninfo_to_redis_hash(hash_prefix="nasb95"):
    """
    insert general version structure info as a Redis hash.

    Args:
        hash_prefix (str): Prefix for Redis hash keys
    """

    r = redis_conn()
    r.hset(hash_prefix, mapping={"name": hash_prefix, "data": "NASB 95 Translation"})

    with open("book_map.json", "r", encoding="utf-8") as f:
        book_map = json.load(f)

    count = 0
    for book in book_map:
        print(f"adding {hash_prefix}:books:{list(book.keys())[0]}")
        r.hset(
            f"{hash_prefix}:books:{list(book.keys())[0]}",
            mapping={"code": list(book.values())[0]},
        )
        count += 1

    print(f"Import complete. Processed {count} rows.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import CSV data to Redis hashes")
    parser.add_argument("csv_file", help="Path to the CSV file to import")
    parser.add_argument("--prefix", default="nasb95", help="Prefix for Redis hash keys")

    args = parser.parse_args()
    load_dotenv()

    versioninfo_to_redis_hash(hash_prefix=args.prefix)
    csv_to_redis_hash(args.csv_file, hash_prefix=args.prefix)
