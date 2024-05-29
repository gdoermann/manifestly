"""
Manifestly resolved settings from environment variables
"""
import os

DEFAULT_HASH_ALGORITHM = os.getenv('MANIFESTLY_HASH_ALGORITHM', 'sha256')
MANIFEST_NAME = os.getenv('MANIFESTLY_NAME', '.manifestly.json')
CHUNK_SIZE = int(os.getenv('MANIFESTLY_CHUNK_SIZE', 8192))
