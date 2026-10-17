#!/usr/bin/env python3
"""Test Qdrant client functionality."""

from qdrant_client import QdrantClient
from qdrant_client.http import models

print("Testing Qdrant client...")

# Try to create client
try:
    client = QdrantClient(path="./qdrant_local_storage")
    print("Client created successfully")

    # Check if search method exists
    if hasattr(client, 'search'):
        print("Search method exists")
    else:
        print("Search method does NOT exist")
        print("Available methods:", [method for method in dir(client) if not method.startswith('_')])

    # Try to get collections
    try:
        collections = client.get_collections()
        print(f"Collections: {[c.name for c in collections.collections]}")
    except Exception as e:
        print(f"Error getting collections: {e}")

except Exception as e:
    print(f"Error creating client: {e}")