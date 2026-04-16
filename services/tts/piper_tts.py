import subprocess


class TTSError(Exception):
    pass


def synthesize(text: str, output_path: str, model_path: str, length_scale: float = 1.2) -> str:
    """
    Run piper TTS to generate a WAV file from text.
    length_scale > 1.0 = slower speech (1.2 = 20% slower).
    Returns output_path on success, raises TTSError on failure.
    """
    result = subprocess.run(
        ["piper", "--model", model_path, "--output_file", output_path,
         "--length_scale", str(length_scale)],
        input=text.encode(),
        capture_output=True,
    )
    if result.returncode != 0:
        raise TTSError(f"Piper failed: {result.stderr.decode()}")
    return output_path
