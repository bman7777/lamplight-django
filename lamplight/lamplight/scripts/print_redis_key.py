#!/usr/bin/env python3

import os
import sys

import redis
from dotenv import load_dotenv


def print_redis_hash(host="localhost", port=6379, db=0, password=None, hash_key=None):
    """
    Print all field-value pairs of a Redis hash.

    Args:
        host (str): Redis server hostname
        port (int): Redis server port
        db (int): Redis database number
        password (str): Redis password (if required)
        hash_key (str): The hash key to retrieve
    """
    # Check if hash_key was provided
    if not hash_key:
        print("Error: Hash key must be provided.")
        print("Usage: python script.py <hash_key>")
        sys.exit(1)

    try:
        # Create Redis connection
        r = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,  # This ensures data is returned as strings, not bytes
        )

        # Check if the key exists
        if not r.exists(hash_key):
            print(f"Hash key '{hash_key}' does not exist.")
            sys.exit(1)

        # Check if the key is a hash
        if r.type(hash_key) != "hash":
            print(
                f"Key '{hash_key}' exists but is not a hash. Type: {r.type(hash_key)}"
            )
            sys.exit(1)

        # Get all fields and values from the hash
        hash_data = r.hgetall(hash_key)

        if not hash_data:
            print(f"Hash key '{hash_key}' exists but is empty.")
        else:
            print(f"Contents of hash key '{hash_key}':")
            for field, value in hash_data.items():
                print(f"  {field}: {value}")

    except redis.ConnectionError:
        print(f"Error: Could not connect to Redis at {host}:{port}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    load_dotenv()

    # Default values
    host = "localhost"
    port = 6379
    db = 0
    password = os.getenv("REDIS_PASS")
    hash_key = None

    # Parse command line arguments
    args = sys.argv[1:]
    print(f"Debug: Command line arguments received: {args}")

    if len(args) >= 1:
        hash_key = args[0]

    print_redis_hash(host, port, db, password, hash_key)
