from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


class YouTubeUploader:
    def __init__(self, channel_type: str):
        self.channel_type = channel_type
        self.service = self.authenticate()

    def authenticate(self):
        token_path = f"tokens/{self.channel_type}.pickle"
        os.makedirs("tokens", exist_ok=True)

        credentials = None

        if os.path.exists(token_path):
            with open(token_path, "rb") as token:
                credentials = pickle.load(token)

        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())

            with open(token_path, "wb") as token:
                pickle.dump(credentials, token)

        if not credentials or not credentials.valid:
            flow = InstalledAppFlow.from_client_secrets_file(
                "client.json", SCOPES
            )
            credentials = flow.run_local_server(port=0)

            with open(token_path, "wb") as token:
                pickle.dump(credentials, token)

        return build("youtube", "v3", credentials=credentials)

    def upload(self, package):
        request = self.service.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": package.title,
                    "description": package.description,
                    "tags": package.hashtags,
                    "categoryId": "22",
                },
                "status": {
                    "privacyStatus": "public",
                },
            },
            media_body=MediaFileUpload(package.video_path, resumable=True),
        )

        response = None

        while response is None:
            status, response = request.next_chunk()

            if status:
                print(
                    f"[YouTubeUploader] Upload progress: {int(status.progress() * 100)}%"
                )

        video_id = response["id"]

        print(
            f"[YouTubeUploader] Uploaded ({self.channel_type}): https://youtube.com/watch?v={video_id}"
        )

        return video_id