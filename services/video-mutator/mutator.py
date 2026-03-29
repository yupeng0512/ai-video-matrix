"""Five-dimension video mutation engine using FFmpeg.

Dimensions:
  1. Pixel-level: resolution, framerate, bitrate, MD5
  2. Visual-level: filters, color shift, crop
  3. Audio-level: pitch, tempo, volume
  4. Structural-level: intro/outro templates, transition effects
  5. Metadata-level: handled by content-planner (titles, tags, covers)
"""
import asyncio
import os
import random
import shutil
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MutationParams:
    brightness: float = 0.0
    contrast: float = 1.0
    saturation: float = 1.0
    hue: float = 0.0
    crop_pct: float = 0.0
    mirror: bool = False
    speed_factor: float = 1.0
    audio_pitch_semitones: float = 0.0
    audio_volume_db: float = 0.0
    fps_delta: int = 0
    crf_delta: int = 0

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


def random_params(intensity: str = "medium") -> MutationParams:
    """Generate random mutation parameters.

    intensity: "low" for subtle changes, "medium" for moderate, "high" for aggressive.
    """
    ranges = {
        "low":    {"b": 0.01, "c": 0.01, "s": 0.02, "h": 1, "crop": 0.01, "pitch": 0.3, "vol": 0.5},
        "medium": {"b": 0.03, "c": 0.03, "s": 0.05, "h": 3, "crop": 0.02, "pitch": 0.5, "vol": 1.0},
        "high":   {"b": 0.06, "c": 0.06, "s": 0.10, "h": 5, "crop": 0.03, "pitch": 1.0, "vol": 2.0},
    }
    r = ranges.get(intensity, ranges["medium"])

    return MutationParams(
        brightness=random.uniform(-r["b"], r["b"]),
        contrast=random.uniform(1 - r["c"], 1 + r["c"]),
        saturation=random.uniform(1 - r["s"], 1 + r["s"]),
        hue=random.uniform(-r["h"], r["h"]),
        crop_pct=random.uniform(0, r["crop"]),
        mirror=random.choice([True, False]),
        speed_factor=random.uniform(0.98, 1.02),
        audio_pitch_semitones=random.uniform(-r["pitch"], r["pitch"]),
        audio_volume_db=random.uniform(-r["vol"], r["vol"]),
        fps_delta=random.choice([-1, 0, 0, 1]),
        crf_delta=random.choice([-2, -1, 0, 1, 2]),
    )


def build_ffmpeg_cmd(input_path: str, output_path: str, params: MutationParams) -> list[str]:
    """Build an FFmpeg command from mutation parameters."""
    vfilters = []

    if params.brightness != 0 or params.contrast != 1.0 or params.saturation != 1.0:
        vfilters.append(
            f"eq=brightness={params.brightness}:contrast={params.contrast}:saturation={params.saturation}"
        )

    if params.hue != 0:
        vfilters.append(f"hue=h={params.hue}")

    if params.crop_pct > 0:
        pct = params.crop_pct
        vfilters.append(f"crop=iw*(1-{pct}):ih*(1-{pct}):iw*{pct/2}:ih*{pct/2}")
        vfilters.append("scale=-2:1080")

    if params.mirror:
        vfilters.append("hflip")

    if params.speed_factor != 1.0:
        vfilters.append(f"setpts={1/params.speed_factor}*PTS")

    afilters = []
    if params.speed_factor != 1.0:
        afilters.append(f"atempo={params.speed_factor}")
    if params.audio_pitch_semitones != 0:
        ratio = 2 ** (params.audio_pitch_semitones / 12)
        afilters.append(f"asetrate=44100*{ratio},aresample=44100")
    if params.audio_volume_db != 0:
        afilters.append(f"volume={params.audio_volume_db}dB")

    cmd = ["ffmpeg", "-y", "-i", input_path]

    if vfilters:
        cmd.extend(["-vf", ",".join(vfilters)])
    if afilters:
        cmd.extend(["-af", ",".join(afilters)])

    base_crf = 23
    crf = max(18, min(28, base_crf + params.crf_delta))
    cmd.extend(["-c:v", "libx264", "-crf", str(crf), "-preset", "fast"])
    cmd.extend(["-c:a", "aac", "-b:a", "128k"])

    if params.fps_delta != 0:
        fps = max(24, 30 + params.fps_delta)
        cmd.extend(["-r", str(fps)])

    cmd.append(output_path)
    return cmd


async def mutate_video(input_path: str, output_path: str, params: MutationParams | None = None) -> MutationParams:
    """Apply mutations to a video file. Returns the params used."""
    if params is None:
        params = random_params()

    cmd = build_ffmpeg_cmd(input_path, output_path, params)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {stderr.decode()[-500:]}")

    return params


async def generate_variants(input_path: str, output_dir: str, count: int = 5, intensity: str = "medium") -> list[dict]:
    """Generate multiple video variants from a single source."""
    os.makedirs(output_dir, exist_ok=True)
    results = []
    for i in range(count):
        params = random_params(intensity)
        variant_name = f"variant_{uuid.uuid4().hex[:8]}.mp4"
        output_path = os.path.join(output_dir, variant_name)
        used_params = await mutate_video(input_path, output_path, params)
        results.append({
            "path": output_path,
            "filename": variant_name,
            "params": used_params.to_dict(),
        })
    return results
