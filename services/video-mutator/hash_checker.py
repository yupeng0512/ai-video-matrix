"""Video similarity checking using perceptual hashing.

Uses videohash to generate 64-bit perceptual hashes, then compares
Hamming distance to detect near-duplicate videos.
"""
import asyncio
import functools
from pathlib import Path

from videohash import VideoHash


def _compute_hash(video_path: str) -> str:
    """Compute perceptual hash for a video file (blocking call)."""
    vh = VideoHash(path=video_path)
    return vh.hash_hex


async def compute_hash(video_path: str) -> str:
    """Async wrapper for perceptual hash computation."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _compute_hash, video_path)


def hamming_distance(hash1: str, hash2: str) -> int:
    """Compute Hamming distance between two hex hash strings."""
    int1 = int(hash1, 16)
    int2 = int(hash2, 16)
    xor = int1 ^ int2
    return bin(xor).count("1")


def similarity_score(hash1: str, hash2: str) -> float:
    """Compute similarity score (0.0 = completely different, 1.0 = identical)."""
    dist = hamming_distance(hash1, hash2)
    max_bits = max(len(hash1), len(hash2)) * 4
    return 1.0 - (dist / max_bits) if max_bits > 0 else 0.0


async def check_similarity(video_path: str, existing_hashes: list[str], threshold: float = 0.70) -> dict:
    """Check if a video is too similar to any existing video.

    Returns:
        {
            "hash": str,
            "is_unique": bool,
            "max_similarity": float,
            "most_similar_hash": str | None,
        }
    """
    video_hash = await compute_hash(video_path)

    max_sim = 0.0
    most_similar = None
    for existing in existing_hashes:
        sim = similarity_score(video_hash, existing)
        if sim > max_sim:
            max_sim = sim
            most_similar = existing

    return {
        "hash": video_hash,
        "is_unique": max_sim < threshold,
        "max_similarity": round(max_sim, 4),
        "most_similar_hash": most_similar if max_sim >= threshold else None,
    }
