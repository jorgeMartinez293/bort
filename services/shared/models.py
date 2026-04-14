# services/shared/models.py
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Bot:
    id: Optional[int]
    name: str
    niche: str
    subreddits: list[str]      # stored as JSON
    schedule_cron: str
    platforms: list[str]       # stored as JSON
    background_mode: str       # "gameplay" | "images" | "random"
    active: bool
    created_at: Optional[datetime] = None

@dataclass
class Content:
    id: Optional[int]
    bot_id: int
    reddit_id: str
    subreddit: str
    raw_title: str
    cleaned_script: str
    upvotes: int
    status: str   # pending | tts_queued | tts_done | render_queued | rendered | skip
    created_at: Optional[datetime] = None

@dataclass
class Video:
    id: Optional[int]
    content_id: int
    bot_id: int
    audio_path: Optional[str]
    video_path: Optional[str]
    duration_secs: Optional[float]
    status: str   # pending_review | approved | rejected | uploading | uploaded
    created_at: Optional[datetime] = None

@dataclass
class Upload:
    id: Optional[int]
    video_id: int
    platform: str
    status: str   # pending | uploading | done | failed
    platform_video_id: Optional[str] = None
    published_at: Optional[datetime] = None
    error_msg: Optional[str] = None
