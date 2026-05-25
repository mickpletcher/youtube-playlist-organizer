from googleapiclient.errors import HttpError

from src.models.playlist import Playlist, PlaylistItem


class YouTubeQuotaExceeded(RuntimeError):
    pass


def _is_quota_exceeded(exc: HttpError) -> bool:
    return "quotaExceeded" in str(exc)


def _execute(request):
    try:
        return request.execute()
    except HttpError as exc:
        if _is_quota_exceeded(exc):
            raise YouTubeQuotaExceeded(
                "YouTube API quota is exhausted. Wait for the quota reset, then export and analyze again before applying more changes."
            ) from exc
        raise


def get_playlists(client) -> list[Playlist]:
    playlists = []
    request = client.playlists().list(
        part="snippet,contentDetails,status",
        mine=True,
        maxResults=50,
    )
    while request:
        response = _execute(request)
        for item in response.get("items", []):
            playlists.append(Playlist(
                id=item["id"],
                title=item["snippet"]["title"],
                description=item["snippet"].get("description", ""),
                item_count=item["contentDetails"]["itemCount"],
                privacy=item["status"]["privacyStatus"],
            ))
        request = client.playlists().list_next(request, response)
    return playlists


def get_playlist_by_id(client, playlist_id: str) -> Playlist | None:
    response = _execute(client.playlists().list(
        part="snippet,contentDetails,status",
        id=playlist_id,
        maxResults=1,
    ))
    items = response.get("items", [])
    if not items:
        return None

    item = items[0]
    return Playlist(
        id=item["id"],
        title=item["snippet"]["title"],
        description=item["snippet"].get("description", ""),
        item_count=item["contentDetails"]["itemCount"],
        privacy=item["status"]["privacyStatus"],
    )


def get_liked_playlist(client) -> Playlist | None:
    response = _execute(client.channels().list(
        part="contentDetails",
        mine=True,
        maxResults=1,
    ))
    items = response.get("items", [])
    if not items:
        return None

    liked_playlist_id = (
        items[0]
        .get("contentDetails", {})
        .get("relatedPlaylists", {})
        .get("likes")
    )
    if not liked_playlist_id:
        return None

    playlist = get_playlist_by_id(client, liked_playlist_id)
    if playlist:
        return playlist

    return Playlist(
        id=liked_playlist_id,
        title="Liked videos",
        description="",
        item_count=0,
        privacy="private",
    )


def get_playlist_items(client, playlist_id: str) -> list[PlaylistItem]:
    items = []
    request = client.playlistItems().list(
        part="snippet",
        playlistId=playlist_id,
        maxResults=50,
    )
    while request:
        response = _execute(request)
        for item in response.get("items", []):
            snippet = item["snippet"]
            items.append(PlaylistItem(
                id=item["id"],
                video_id=snippet["resourceId"]["videoId"],
                title=snippet["title"],
                position=snippet["position"],
                playlist_id=playlist_id,
            ))
        request = client.playlistItems().list_next(request, response)
    return items


def delete_playlist_item(client, playlist_item_id: str) -> None:
    try:
        _execute(client.playlistItems().delete(id=playlist_item_id))
        return True
    except HttpError as exc:
        if "playlistItemNotFound" in str(exc):
            return False
        raise


def add_video_to_playlist(client, playlist_id: str, video_id: str, position: int | None = None) -> None:
    snippet = {
        "playlistId": playlist_id,
        "resourceId": {
            "kind": "youtube#video",
            "videoId": video_id,
        },
    }
    if position is not None:
        snippet["position"] = position

    try:
        _execute(client.playlistItems().insert(
            part="snippet",
            body={"snippet": snippet},
        ))
    except HttpError as exc:
        if position is None or "manualSortRequired" not in str(exc):
            raise

        snippet.pop("position", None)
        _execute(client.playlistItems().insert(
            part="snippet",
            body={"snippet": snippet},
        ))


def create_playlist(
    client,
    title: str,
    description: str = "",
    privacy: str = "private",
) -> str:
    response = _execute(client.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
            },
            "status": {
                "privacyStatus": privacy,
            },
        },
    ))
    return response["id"]


def delete_playlist(client, playlist_id: str) -> None:
    _execute(client.playlists().delete(id=playlist_id))
