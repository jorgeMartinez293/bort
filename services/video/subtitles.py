# services/video/subtitles.py

# ASS color format is AABBGGRR: amber #e8a020 → R=0xe8, G=0xa0, B=0x20 → &H0020A0E8&
HIGHLIGHT_COLOR = "{\\c&H0020A0E8&}"  # amber
RESET_COLOR = "{\\c&HFFFFFF&}"        # white

def format_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

_ASS_HEADER_TMPL = """\
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style_line}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

# Alignment 5 = center-center (default, no image)
_STYLE_CENTER = "Style: Default,Syne,88,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,0,5,50,50,0,1"

def _ass_header(subtitle_top_y: int = 0) -> str:
    if subtitle_top_y > 0:
        # Alignment 8 = top-center; MarginV = pixels from top edge → text starts right below image
        style = f"Style: Default,Syne,80,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,0,8,60,60,{subtitle_top_y},1"
    else:
        style = _STYLE_CENTER
    return _ASS_HEADER_TMPL.format(style_line=style)

def timestamps_to_ass(words: list[dict], words_per_chunk: int = 3, with_image: bool = False, subtitle_top_y: int = 0) -> str:
    """
    Convert word timestamps to ASS subtitle format.
    Groups words into chunks of words_per_chunk.
    Within each chunk, the currently-speaking word is highlighted in amber.
    """
    header = _ass_header(subtitle_top_y)
    if not words:
        return header

    lines = [header]

    # Group into chunks
    chunks = [words[i:i+words_per_chunk] for i in range(0, len(words), words_per_chunk)]

    for chunk in chunks:
        # For each word in chunk, produce one subtitle line where that word is highlighted
        for active_idx, active_word in enumerate(chunk):
            word_start = active_word["start"]
            word_end = active_word["end"]
            # Build text with active word highlighted
            parts = []
            for i, w in enumerate(chunk):
                if i == active_idx:
                    parts.append(f"{HIGHLIGHT_COLOR}{w['word']}{RESET_COLOR}")
                else:
                    parts.append(w["word"])
            text = " ".join(parts)
            lines.append(
                f"Dialogue: 0,{format_ass_time(word_start)},{format_ass_time(word_end)},"
                f"Default,,0,0,0,,{text}"
            )

    return "\n".join(lines)
