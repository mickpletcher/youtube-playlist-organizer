from pydantic import BaseModel


class Playlist(BaseModel):
    id: str
    title: str
    description: str
    item_count: int
    privacy: str


class PlaylistItem(BaseModel):
    id: str
    video_id: str
    title: str
    position: int
    playlist_id: str
