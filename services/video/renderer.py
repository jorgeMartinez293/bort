import os, subprocess, random, glob


class RenderError(Exception):
    pass


def pick_background_clip(backgrounds_dir: str) -> str:
    """Pick a random .mp4 file from a directory tree."""
    clips = glob.glob(os.path.join(backgrounds_dir, "**", "*.mp4"), recursive=True)
    if not clips:
        raise RenderError(f"No .mp4 background clips found in {backgrounds_dir}")
    return random.choice(clips)


def build_ffmpeg_cmd(
    background: str,
    audio: str,
    subtitles: str,
    output: str,
    bg_start: float,
    duration: float,
) -> list:
    encoder = os.environ.get("VIDEO_ENCODER", "libx264")
    # Escape subtitles path for ffmpeg filter
    subs_escaped = subtitles.replace(":", "\\:").replace("'", "\\'")

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(bg_start),
        "-i", background,
        "-i", audio,
        "-t", str(duration),
        "-vf", (
            f"scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,"
            f"ass={subs_escaped}"
        ),
        "-c:v", encoder,
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        output
    ]
    return cmd


def render(
    background: str,
    audio: str,
    subtitles: str,
    output: str,
    duration: float,
) -> str:
    """Render final video. Returns output path on success."""
    bg_start = random.uniform(5, 30)
    cmd = build_ffmpeg_cmd(background, audio, subtitles, output, bg_start, duration)
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RenderError(f"FFmpeg failed: {result.stderr.decode()[-500:]}")
    return output
