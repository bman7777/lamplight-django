import argparse
import os
from collections import deque

import redis
from dotenv import load_dotenv


def traverse_tree(
    redis_host="localhost",
    redis_port=6379,
    redis_db=0,
    root_key="nasb95",
    separator=":",
):
    """
    Traverse a tree structure stored in Redis hash sets, starting from the root.

    The tree is assumed to be stored with:
    - Node data as hashes: {node_prefix}:{id} → hash with fields
    - Children stored in sets: {children_prefix}:{id} → set of child IDs

    Args:
        redis_host (str): Redis server hostname
        redis_port (int): Redis server port
        redis_db (int): Redis database number
        root_key (str): The key of the root node
        node_prefix (str): Prefix used for node keys
        children_prefix (str): Prefix used for children set keys
    """
    # Connect to Redis
    r = redis.Redis(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        password=os.getenv("REDIS_PASS"),
        decode_responses=True,  # Automatically decode responses to strings
    )

    # Check connection
    try:
        r.ping()
        print(f"Connected to Redis at {redis_host}:{redis_port}")
    except redis.ConnectionError as e:
        print(f"Failed to connect to Redis: {e}")
        return

    # Check if root exists
    if not r.exists(root_key):
        print(f"Root node {root_key} does not exist")
        return

    # Print the tree header
    print("\n🌳 REDIS HIERARCHICAL TREE STRUCTURE 🌳")
    print("=" * 60)

    # Find all keys with the hierarchical pattern
    pattern = f"{root_key}{separator}*" if root_key != "*" else "*"
    all_keys = r.keys(pattern)
    all_keys.append(root_key)  # Add the root key itself

    # Build a tree structure in memory
    tree = {}
    for key in all_keys:
        add_node_to_tree(tree, key, separator)

    # Print the tree
    print_tree(r, tree, 0, separator)

    print("=" * 60)
    print(f"Tree traversal complete. Found {len(all_keys)} nodes.")


def add_node_to_tree(tree, key, separator):
    """Add a node to the in-memory tree structure."""
    parts = key.split(separator)
    current = tree

    # Navigate/create the path in the tree
    for i, part in enumerate(parts):
        if part not in current:
            current[part] = {}
        current = current[part]


def print_tree(redis_client, tree, depth=0, separator=":", path=None):
    """Print the tree structure recursively."""
    if path is None:
        path = []

    for key_part, children in sorted(tree.items()):
        # Calculate the full Redis key for this node
        current_path = path + [key_part]
        full_key = separator.join(current_path)

        # Get node data from Redis
        node_data = redis_client.hgetall(full_key)

        # Print node information with indentation based on depth
        indent = "  " * depth
        print(f"{indent}{key_part}")

        if node_data:
            for field, value in node_data.items():
                print(f"{indent}  - {field}: {value}")

        # Recursively print children
        print_tree(redis_client, children, depth + 1, separator, current_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Traverse and print a tree structure stored in Redis"
    )
    parser.add_argument("--host", default="localhost", help="Redis server hostname")
    parser.add_argument("--port", type=int, default=6379, help="Redis server port")
    parser.add_argument("--db", type=int, default=0, help="Redis database number")
    parser.add_argument("--root", default="nasb95", help="Key of the root node")
    parser.add_argument(
        "--separator", default=":", help="Separator used in hierarchical keys"
    )

    args = parser.parse_args()
    load_dotenv()

    try:
        traverse_tree(
            redis_host=args.host,
            redis_port=args.port,
            redis_db=args.db,
            root_key=args.root,
            separator=args.separator,
        )
    except Exception as e:
        print(f"Error: {e}")
