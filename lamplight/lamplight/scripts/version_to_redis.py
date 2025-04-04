import argparse
import csv
import os.path

import redis
from dotenv import load_dotenv


def csv_to_redis_hash(hash_prefix="nasb95"):
    """
    insert each row as a Redis hash.

    Args:
        hash_prefix (str): Prefix for Redis hash keys
    """

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

    r.hset(hash_prefix, mapping={"name": hash_prefix, "data": "NASB 95 Translation"})

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
    count = 0
    for book in book_map:
        r.hset(
            f"{hash_prefix}:books:{list(book.keys())[0]}",
            mapping={"code": list(book.values())[0]},
        )
        count += 1

    print(f"Import complete. Processed {count} rows.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import CSV data to Redis hashes")
    parser.add_argument("--prefix", default="nasb95", help="Prefix for Redis hash keys")

    args = parser.parse_args()
    load_dotenv()

    try:
        csv_to_redis_hash(hash_prefix=args.prefix)
    except Exception as e:
        print(f"Error: {e}")
