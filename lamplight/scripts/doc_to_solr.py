#!/usr/bin/env python3
"""
Script to batch update documents from a large JSON file to a Solr collection.
This helps prevent connection reset errors when adding thousands of documents.
"""

import argparse
import json
import os
import sys
import time

import pysolr
from dotenv import load_dotenv
from tqdm import tqdm

# pragma pylint: disable=broad-exception-caught


def batch_upload_to_solr(
    json_file_path,
    batch_size=500,
    commit_each_batch=True,
    timeout=920,
    clear_collection=True,
):
    """
    Upload documents from a JSON file to Solr in batches.

    Args:
        json_file_path (str): Path to the JSON file containing documents.
        batch_size (int): Number of documents to send in each batch.
        commit_each_batch (bool): Whether to commit after each batch.
        timeout (int): Connection and request timeout in seconds.
        clear_collection (bool): Whether to clear all existing documents before adding new ones.
    """

    solr_url = "http://localhost:8983/solr/verses"

    # Connect to Solr with increased timeout
    try:
        solr = pysolr.Solr(
            solr_url,
            timeout=timeout,
            auth=(os.getenv("SOLR_USER"), os.getenv("SOLR_PASS")),
        )
        # Test connection
        solr.ping()
        print(f"Successfully connected to Solr at {solr_url}")

        # Clear the collection if requested
        if clear_collection:
            print("Clearing all documents from the collection...")
            try:
                solr.delete(q="*:*")
                solr.commit()
                print("Collection cleared successfully")
            except Exception as clear_err:
                print(f"Error clearing collection: {clear_err}")
                response = input("Continue with upload anyway? (y/n): ")
                if response.lower() != "y":
                    sys.exit(1)
    except Exception as e:
        print(f"Failed to connect to Solr: {e}")
        sys.exit(1)

    # Load documents from JSON file
    try:
        print(f"Loading documents from {json_file_path}...")
        with open(json_file_path, "r", encoding="utf-8") as f:
            all_docs = json.load(f)

        total_docs = len(all_docs)
        print(f"Loaded {total_docs} documents")
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        sys.exit(1)

    # Upload documents in batches with progress bar
    successful_docs = 0
    failed_batches = 0

    print(f"Uploading documents in batches of {batch_size}...")
    progress_bar = tqdm(total=total_docs, unit="docs")

    for i in range(0, total_docs, batch_size):
        batch = all_docs[i : i + batch_size]
        batch_num = i // batch_size + 1

        try:
            # Add batch to Solr
            solr.add(batch, commit=commit_each_batch)
            successful_docs += len(batch)

            # Update progress bar
            progress_bar.update(len(batch))

            # Optional delay between batches to reduce server load
            time.sleep(0.1)

        except Exception as e:
            failed_batches += 1
            print(f"\nError in batch {batch_num}: {e}")
            print("Retrying after a short delay...")

            # Wait and retry once with smaller batch size
            time.sleep(5)
            try:
                # Try with half the batch size
                half_batch = batch[: len(batch) // 2]
                solr.add(half_batch, commit=commit_each_batch)
                successful_docs += len(half_batch)
                progress_bar.update(len(half_batch))

                # Try the second half
                half_batch = batch[len(batch) // 2 :]
                solr.add(half_batch, commit=commit_each_batch)
                successful_docs += len(half_batch)
                progress_bar.update(len(half_batch))
            except Exception as retry_err:
                print(f"Retry failed: {retry_err}")
                print(f"Skipping batch {batch_num} and continuing...")

    progress_bar.close()

    # Final commit if not committing each batch
    if not commit_each_batch:
        try:
            print("Performing final commit...")
            solr.commit()
        except Exception as e:
            print(f"Error during final commit: {e}")

    # Print summary
    print("\nUpload Summary:")
    print(f"Total documents processed: {total_docs}")
    print(f"Successfully uploaded: {successful_docs}")
    print(f"Failed batches: {failed_batches}")
    print(f"Success rate: {(successful_docs/total_docs)*100:.2f}%")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Upload documents to Solr in batches from a JSON file"
    )
    parser.add_argument("json_file", help="Path to the JSON file containing documents")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Number of documents per batch (default: 500)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=920,
        help="Connection timeout in seconds (default: 120)",
    )
    parser.add_argument(
        "--no-commit",
        action="store_false",
        help="Don't commit after each batch (only at the end)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all existing documents from the collection before adding new ones",
    )

    args = parser.parse_args()
    load_dotenv()

    batch_upload_to_solr(
        args.json_file,
        batch_size=args.batch_size,
        commit_each_batch=not args.no_commit,
        timeout=args.timeout,
        clear_collection=args.clear,
    )
