import os
import pytest
from services.video.renderer import build_ffmpeg_cmd, pick_background_clip


@pytest.fixture(autouse=True)
def restore_video_encoder():
    original = os.environ.get("VIDEO_ENCODER")
    yield
    if original is None:
        os.environ.pop("VIDEO_ENCODER", None)
    else:
        os.environ["VIDEO_ENCODER"] = original


def test_build_ffmpeg_cmd_uses_env_encoder():
    os.environ["VIDEO_ENCODER"] = "libx264"
    cmd = build_ffmpeg_cmd(
        background="/media/bg.mp4",
        audio="/media/audio.wav",
        subtitles="/media/subs.ass",
        output="/media/out.mp4",
        bg_start=10.0,
        duration=45.0,
    )
    assert "libx264" in cmd
    assert "/media/out.mp4" in cmd
    assert "-t" in cmd
    assert "45.0" in cmd


def test_build_ffmpeg_cmd_uses_hw_encoder_when_set():
    os.environ["VIDEO_ENCODER"] = "h264_v4l2m2m"
    cmd = build_ffmpeg_cmd(
        background="/media/bg.mp4",
        audio="/media/audio.wav",
        subtitles="/media/subs.ass",
        output="/media/out.mp4",
        bg_start=10.0,
        duration=45.0,
    )
    assert "h264_v4l2m2m" in cmd


def test_pick_background_clip_returns_file_from_dir(tmp_path):
    (tmp_path / "clip1.mp4").write_bytes(b"")
    (tmp_path / "clip2.mp4").write_bytes(b"")
    result = pick_background_clip(str(tmp_path))
    assert result.endswith(".mp4")
    assert "clip" in result
