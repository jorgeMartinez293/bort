import subprocess


class TTSError(Exception):
    pass


def synthesize(text: str, output_path: str, model_path: str) -> str:
    """
    Run piper TTS to generate a WAV file from text.
    Returns output_path on success, raises TTSError on failure.
    """
    result = subprocess.run(
        ["piper", "--model", model_path, "--output_file", output_path],
        input=text.encode(),
        capture_output=True,
    )
    if result.returncode != 0:
        raise TTSError(f"Piper failed: {result.stderr.decode()}")
    return output_path
