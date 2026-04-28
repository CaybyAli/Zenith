from enum import Enum


class TrendSourceType(str, Enum):
    MANUAL = "manual"
    RSS = "rss"
    API = "api"
    SOCIAL_SCRAPE = "social_scrape"
    INTERNAL_OBSERVATION = "internal_observation"


class TrendPlatform(str, Enum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    X = "x"
    REDDIT = "reddit"
    WEB = "web"
    UNKNOWN = "unknown"