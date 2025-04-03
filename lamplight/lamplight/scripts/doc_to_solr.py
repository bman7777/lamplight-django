#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv


def post_to_solr(json_file, solr_url, collection):
    """
    Post JSON documents to a Solr collection

    Args:
        json_file (str): Path to the JSON file containing documents
        solr_url (str): Base URL of the Solr instance (e.g., 'http://localhost:8983/solr')
        collection (str): Name of the Solr collection

    Returns:
        bool: True if operation was successful, False otherwise
    """
    # Construct the full Solr update URL
    update_url = f"{solr_url}/{collection}/update/json/docs"
    auth = (os.getenv("SOLR_USER"), os.getenv("SOLR_PASS"))

    try:
        # Read the JSON file
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # If data is a list, we'll post each document individually
        if isinstance(data, list):
            print(f"Posting {len(data)} documents to Solr...")

            # Set up the headers
            headers = {"Content-type": "application/json"}

            # Post each document
            for i, doc in enumerate(data):
                response = requests.post(
                    update_url, json=doc, headers=headers, auth=auth
                )

                if response.status_code != 200:
                    print(
                        f"Error posting document {i+1}: {response.text}",
                        file=sys.stderr,
                    )
                    return False

                if (i + 1) % 100 == 0:
                    print(f"Posted {i+1} documents...")

            # Commit the changes
            commit_url = f"{solr_url}/{collection}/update"
            response = requests.get(f"{commit_url}?commit=true", auth=auth)

            if response.status_code != 200:
                print(f"Error committing changes: {response.text}", file=sys.stderr)
                return False

            print(f"Successfully posted {len(data)} documents to Solr")
            return True
        else:
            # If data is a single document
            print("Posting single document to Solr...")

            # Set up the headers
            headers = {"Content-type": "application/json"}

            # Post the document
            response = requests.post(update_url, json=data, headers=headers, auth=auth)

            if response.status_code != 200:
                print(f"Error posting document: {response.text}", file=sys.stderr)
                return False

            # Commit the changes
            commit_url = f"{solr_url}/{collection}/update"
            response = requests.get(f"{commit_url}?commit=true", auth=auth)

            if response.status_code != 200:
                print(f"Error committing changes: {response.text}", file=sys.stderr)
                return False

            print("Successfully posted document to Solr")
            return True

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return False


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Post JSON documents to Solr")
    parser.add_argument("json_file", help="Path to the JSON file containing documents")
    parser.add_argument(
        "-u",
        "--url",
        default="http://localhost:8983/solr",
        help="Solr base URL (default: http://localhost:8983/solr)",
    )
    parser.add_argument(
        "-c", "--collection", required=True, help="Name of the Solr collection"
    )

    # Parse arguments
    args = parser.parse_args()
    load_dotenv()

    # Check if the JSON file exists
    if not Path(args.json_file).is_file():
        print(f"Error: JSON file '{args.json_file}' not found", file=sys.stderr)
        sys.exit(1)

    # Post the documents to Solr
    success = post_to_solr(
        args.json_file,
        args.url,
        args.collection,
    )

    # Exit with appropriate status code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
