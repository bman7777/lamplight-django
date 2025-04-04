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

    r.hset(f"{hash_prefix}:luk", mapping={"name": "luk", "data": "Luke"})
    r.hset(f"{hash_prefix}:luk:1", mapping={"name": "luk 1", "data": "Luke Chapter 1"})

    # Set up a custom dialect that preserves escaped characters (otherwise we will lose all commas)
    csv.register_dialect(
        "escaped", escapechar="\\", doublequote=False, quoting=csv.QUOTE_MINIMAL
    )

    # Open and process the CSV file
    with open(csv_file, "r", newline="", encoding="utf-8") as file:
        reader = csv.reader(file, dialect="escaped")

        # Process data rows
        row_count = 0
        for row in reader:
            if not row:  # Skip empty rows
                continue

            try:
                # Insert the hash into Redis
                r.hset(
                    f"{hash_prefix}:{row[0]}:{row[1]}:{row[2]}",
                    mapping={"name": f"{row[0]} {row[1]}:{row[2]}", "data": row[3]},
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
