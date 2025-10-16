import os
import google.oauth2.credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi

# This variable specifies the name of a file that contains the OAuth 2.0
# client secret information for your application, including your client ID and
# client secret.
CLIENT_SECRETS_FILE = "client_secret.json"

# This OAuth 2.0 access scope allows for full read access to the
# authenticated user's account, but not write access.
SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

def get_authenticated_service(credentials):
    return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)

def get_user_credentials(authorization_code):
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri='http://localhost:8501'
    )
    flow.fetch_token(authorization_code=authorization_code)
    return flow.credentials

def get_authorization_url():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri='http://localhost:8501'
    )
    authorization_url, _ = flow.authorization_url(prompt='consent')
    return authorization_url

def get_my_videos(credentials, max_results=10):
    youtube = get_authenticated_service(credentials)

    search_response = youtube.search().list(
        part='snippet',
        forMine=True,
        type='video',
        maxResults=max_results
    ).execute()

    videos = []
    for item in search_response.get('items', []):
        video_id = item['id']['videoId']
        title = item['snippet']['title']
        videos.append({'video_id': video_id, 'title': title})

    return videos

def get_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = ' '.join([item['text'] for item in transcript_list])
        return transcript
    except Exception as e:
        return f"Could not retrieve transcript: {e}"