import os, subprocess, random, glob, json


class RenderError(Exception):
    pass


def pick_background_clip(backgrounds_dir: str) -> str:
    """Pick a random .mp4 file from a directory tree."""
    clips = glob.glob(os.path.join(backgrounds_dir, "**", "*.mp4"), recursive=True)
    if not clips:
        raise RenderError(f"No .mp4 background clips found in {backgrounds_dir}")
    return random.choice(clips)


def get_clip_duration(path: str) -> float:
    """Return duration in seconds of a video file using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_entries", "format=duration",
            path,
        ],
        capture_output=True,
    )
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def pick_music_track(music_dir: str) -> "str | None":
    """Pick a random mp3/wav from music_dir. Returns None if dir is missing or empty."""
    if not os.path.isdir(music_dir):
        return None
    tracks = glob.glob(os.path.join(music_dir, "**", "*.mp3"), recursive=True)
    tracks += glob.glob(os.path.join(music_dir, "**", "*.wav"), recursive=True)
    return random.choice(tracks) if tracks else None


def build_ffmpeg_cmd(
    background: str,
    audio: str,
    subtitles: str,
    output: str,
    bg_start: float,
    duration: float,
    music: "str | None" = None,
    music_volume: float = 0.25,
    image_path: "str | None" = None,
    image_top_y: int = 0,
) -> list:
    encoder = os.environ.get("VIDEO_ENCODER", "libx264")
    subs_escaped = subtitles.replace(":", "\\:").replace("'", "\\'")

    if image_path:
        # Image floats centered over gameplay background; subtitles sit below it
        img_idx = 3 if music else 2
        # Scale image to fit within 900×720 (no crop, no black bars — gameplay shows through)
        img_filter = (
            f"[{img_idx}:v]scale=900:720:force_original_aspect_ratio=decrease[img];"
        )
        # overlay=(W-w)/2:image_top_y  →  horizontally centered, vertically centered
        if music:
            filter_complex = (
                f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[bg];"
                f"{img_filter}"
                f"[bg][img]overlay=(W-w)/2:{image_top_y},ass={subs_escaped}[vout];"
                f"[1:a]volume=1.0[tts];"
                f"[2:a]aloop=loop=-1:size=2147483647,volume={music_volume}[mus];"
                f"[tts][mus]amix=inputs=2:duration=longest:normalize=0[aout]"
            )
            inputs = ["-i", background, "-i", audio, "-i", music, "-i", image_path]
            maps = ["-map", "[vout]", "-map", "[aout]"]
        else:
            filter_complex = (
                f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[bg];"
                f"{img_filter}"
                f"[bg][img]overlay=(W-w)/2:{image_top_y},ass={subs_escaped}[vout]"
            )
            inputs = ["-i", background, "-i", audio, "-i", image_path]
            maps = ["-map", "[vout]", "-map", "1:a"]
        cmd = (
            ["ffmpeg", "-y", "-ss", str(bg_start)]
            + inputs
            + ["-t", str(duration), "-filter_complex", filter_complex]
            + maps
            + ["-c:v", encoder, "-c:a", "aac", "-b:a", "128k", output]
        )
    elif music:
        filter_complex = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,"
            f"ass={subs_escaped}[vout];"
            f"[1:a]volume=1.0[tts];"
            f"[2:a]aloop=loop=-1:size=2147483647,volume={music_volume}[mus];"
            f"[tts][mus]amix=inputs=2:duration=longest:normalize=0[aout]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(bg_start),
            "-i", background,
            "-i", audio,
            "-i", music,
            "-t", str(duration),
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", "[aout]",
            "-c:v", encoder,
            "-c:a", "aac",
            "-b:a", "128k",
            output,
        ]
    else:
        vf = (
            f"scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,"
            f"ass={subs_escaped}"
        )
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(bg_start),
            "-i", background,
            "-i", audio,
            "-t", str(duration),
            "-vf", vf,
            "-c:v", encoder,
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            output,
        ]
    return cmd


def render(
    background: str,
    audio: str,
    subtitles: str,
    output: str,
    duration: float,
    music: "str | None" = None,
    music_volume: float = 0.25,
    image_path: "str | None" = None,
    image_top_y: int = 0,
) -> str:
    """Render final video. Returns output path on success."""
    clip_duration = get_clip_duration(background)
    max_start = max(5.0, clip_duration - duration - 30)
    bg_start = random.uniform(5, max_start) if max_start > 5 else 5.0
    cmd = build_ffmpeg_cmd(
        background, audio, subtitles, output, bg_start, duration,
        music=music, music_volume=music_volume, image_path=image_path, image_top_y=image_top_y,
    )
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RenderError(f"FFmpeg failed: {result.stderr.decode()[-500:]}")
    return output
