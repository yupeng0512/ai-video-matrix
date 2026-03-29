"""Video Mutator API — FFmpeg mutation + videohash similarity checking."""
import os
import tempfile
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from minio import Minio

from config import settings
from mutator import mutate_video, generate_variants, random_params, MutationParams
from hash_checker import compute_hash, check_similarity


def _get_minio() -> Minio:
    endpoint = settings.minio_endpoint.replace("http://", "").replace("https://", "")
    return Minio(
        endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_endpoint.startswith("https"),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = _get_minio()
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)
    yield


app = FastAPI(title="Video Mutator", lifespan=lifespan)


class MutateRequest(BaseModel):
    minio_key: str
    variant_count: int = 5
    intensity: str = "medium"


class MutateResult(BaseModel):
    variants: list[dict]


class HashCheckRequest(BaseModel):
    minio_key: str
    existing_hashes: list[str] = []
    threshold: float = 0.70


class HashCheckResult(BaseModel):
    hash: str
    is_unique: bool
    max_similarity: float
    most_similar_hash: str | None = None


@app.post("/mutate", response_model=MutateResult)
async def mutate_endpoint(body: MutateRequest):
    """Download video from MinIO, generate variants, upload them back."""
    client = _get_minio()

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "source.mp4")
        client.fget_object(settings.minio_bucket, body.minio_key, input_path)

        output_dir = os.path.join(tmpdir, "variants")
        results = await generate_variants(
            input_path, output_dir, count=body.variant_count, intensity=body.intensity,
        )

        uploaded = []
        for r in results:
            variant_key = f"variants/{uuid.uuid4().hex}/{r['filename']}"
            client.fput_object(settings.minio_bucket, variant_key, r["path"])

            video_hash = await compute_hash(r["path"])
            uploaded.append({
                "minio_key": variant_key,
                "hash": video_hash,
                "params": r["params"],
            })

    return MutateResult(variants=uploaded)


@app.post("/hash", response_model=HashCheckResult)
async def hash_check_endpoint(body: HashCheckRequest):
    """Download video from MinIO and check similarity against existing hashes."""
    client = _get_minio()

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "check.mp4")
        client.fget_object(settings.minio_bucket, body.minio_key, input_path)
        result = await check_similarity(input_path, body.existing_hashes, body.threshold)

    return HashCheckResult(**result)


@app.post("/mutate-file")
async def mutate_file_endpoint(
    file: UploadFile = File(...),
    variant_count: int = Form(default=3),
    intensity: str = Form(default="medium"),
):
    """Accept a video file upload, generate variants, return them via MinIO keys."""
    client = _get_minio()

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, file.filename or "input.mp4")
        with open(input_path, "wb") as f:
            content = await file.read()
            f.write(content)

        source_key = f"originals/{uuid.uuid4().hex}/{file.filename}"
        client.fput_object(settings.minio_bucket, source_key, input_path)

        output_dir = os.path.join(tmpdir, "variants")
        results = await generate_variants(input_path, output_dir, count=variant_count, intensity=intensity)

        uploaded = []
        for r in results:
            variant_key = f"variants/{uuid.uuid4().hex}/{r['filename']}"
            client.fput_object(settings.minio_bucket, variant_key, r["path"])
            video_hash = await compute_hash(r["path"])
            uploaded.append({
                "minio_key": variant_key,
                "source_key": source_key,
                "hash": video_hash,
                "params": r["params"],
            })

    return {"source_key": source_key, "variants": uploaded}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "video-mutator"}
