import os
import pytest
from services.video.renderer import build_ffmpeg_cmd, pick_background_clip, pick_music_track


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


def test_build_ffmpeg_cmd_maps_tts_audio():
    """Without music: uses -vf, TTS is direct audio input, no filter_complex."""
    os.environ["VIDEO_ENCODER"] = "libx264"
    cmd = build_ffmpeg_cmd(
        background="/media/bg.mp4",
        audio="/media/audio.wav",
        subtitles="/media/subs.ass",
        output="/media/out.mp4",
        bg_start=10.0,
        duration=45.0,
    )
    assert "-vf" in cmd
    assert "-filter_complex" not in cmd
    assert "-shortest" in cmd
    assert "/media/audio.wav" in cmd


def test_build_ffmpeg_cmd_bg_volume_default():
    """bg_volume param is accepted; without music it has no effect on the command."""
    os.environ["VIDEO_ENCODER"] = "libx264"
    cmd = build_ffmpeg_cmd(
        background="/media/bg.mp4",
        audio="/media/audio.wav",
        subtitles="/media/subs.ass",
        output="/media/out.mp4",
        bg_start=10.0,
        duration=45.0,
    )
    # Without music, no filter_complex → bg_volume not in command
    assert "-filter_complex" not in cmd


def test_build_ffmpeg_cmd_no_music_uses_shortest():
    """Without music: uses -shortest so output ends with TTS audio."""
    os.environ["VIDEO_ENCODER"] = "libx264"
    cmd = build_ffmpeg_cmd(
        background="/media/bg.mp4",
        audio="/media/audio.wav",
        subtitles="/media/subs.ass",
        output="/media/out.mp4",
        bg_start=10.0,
        duration=45.0,
    )
    assert "-shortest" in cmd
    assert "-vf" in cmd


def test_pick_background_clip_returns_file_from_dir(tmp_path):
    (tmp_path / "clip1.mp4").write_bytes(b"")
    (tmp_path / "clip2.mp4").write_bytes(b"")
    result = pick_background_clip(str(tmp_path))
    assert result.endswith(".mp4")
    assert "clip" in result


# ---------------------------------------------------------------------------
# pick_music_track
# ---------------------------------------------------------------------------

def test_pick_music_track_returns_file_when_present(tmp_path):
    (tmp_path / "song1.mp3").write_bytes(b"")
    (tmp_path / "song2.wav").write_bytes(b"")
    result = pick_music_track(str(tmp_path))
    assert result is not None
    assert result.endswith((".mp3", ".wav"))


def test_pick_music_track_returns_none_when_empty(tmp_path):
    result = pick_music_track(str(tmp_path))
    assert result is None


def test_pick_music_track_returns_none_when_dir_missing():
    result = pick_music_track("/nonexistent/path/does/not/exist")
    assert result is None


# ---------------------------------------------------------------------------
# build_ffmpeg_cmd — music params
# ---------------------------------------------------------------------------

def test_build_ffmpeg_cmd_no_music_uses_two_inputs():
    os.environ["VIDEO_ENCODER"] = "libx264"
    cmd = build_ffmpeg_cmd(
        background="/media/bg.mp4",
        audio="/media/audio.wav",
        subtitles="/media/subs.ass",
        output="/media/out.mp4",
        bg_start=10.0,
        duration=15.0,
    )
    assert "-filter_complex" not in cmd
    assert "-vf" in cmd
    assert cmd.count("-i") == 2


def test_build_ffmpeg_cmd_with_music_uses_three_inputs():
    os.environ["VIDEO_ENCODER"] = "libx264"
    cmd = build_ffmpeg_cmd(
        background="/media/bg.mp4",
        audio="/media/audio.wav",
        subtitles="/media/subs.ass",
        output="/media/out.mp4",
        bg_start=10.0,
        duration=15.0,
        music="/media/music/track.mp3",
        music_volume=0.25,
    )
    fc = cmd[cmd.index("-filter_complex") + 1]
    # Mixes TTS ([1:a]) + music ([2:a]) — background has no audio so [0:a] is skipped
    assert "amix=inputs=2" in fc
    assert "[1:a]" in fc
    assert "[2:a]" in fc
    assert "aloop" in fc
    assert "volume=0.25" in fc
    assert "/media/music/track.mp3" in cmd
    assert cmd.count("-i") == 3


def test_build_ffmpeg_cmd_music_volume_custom():
    os.environ["VIDEO_ENCODER"] = "libx264"
    cmd = build_ffmpeg_cmd(
        background="/media/bg.mp4",
        audio="/media/audio.wav",
        subtitles="/media/subs.ass",
        output="/media/out.mp4",
        bg_start=10.0,
        duration=15.0,
        music="/media/music/track.mp3",
        music_volume=0.10,
    )
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "volume=0.1" in fc
