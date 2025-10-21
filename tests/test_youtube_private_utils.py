import unittest
from unittest.mock import patch, MagicMock
from src.youtube_private_utils import (
    get_authenticated_service,
    get_user_credentials,
    get_authorization_url,
    get_my_videos,
    get_transcript,
    list_my_channels,
)

class TestYoutubePrivateUtils(unittest.TestCase):

    @patch('src.youtube_private_utils.build')
    def test_get_authenticated_service(self, mock_build):
        mock_credentials = MagicMock()
        get_authenticated_service(mock_credentials)
        mock_build.assert_called_once_with('youtube', 'v3', credentials=mock_credentials)

    @patch('src.youtube_private_utils.Flow.from_client_secrets_file')
    def test_get_user_credentials(self, mock_flow):
        mock_flow_instance = MagicMock()
        mock_flow.return_value = mock_flow_instance

        get_user_credentials('test_auth_code')

        mock_flow.assert_called_once()
        mock_flow_instance.fetch_token.assert_called_once_with(code='test_auth_code')

    @patch('src.youtube_private_utils.Flow.from_client_secrets_file')
    def test_get_authorization_url(self, mock_flow):
        mock_flow_instance = MagicMock()
        mock_flow_instance.authorization_url.return_value = ('test_url', 'test_state')
        mock_flow.return_value = mock_flow_instance

        url = get_authorization_url()

        self.assertEqual(url, 'test_url')
        mock_flow.assert_called_once()
        mock_flow_instance.authorization_url.assert_called_once_with(
            prompt='consent',
            access_type='offline',
            include_granted_scopes='true'
        )

    @patch('src.youtube_private_utils.get_authenticated_service')
    def test_get_my_videos(self, mock_get_service):
        mock_youtube = MagicMock()
        mock_get_service.return_value = mock_youtube

        mock_playlist_response = {
            'items': [
                {
                    'contentDetails': {'videoId': 'video1', 'videoPublishedAt': '2024-01-01T00:00:00Z'},
                    'snippet': {'title': 'Title 1'},
                },
                {
                    'contentDetails': {'videoId': 'video2', 'videoPublishedAt': '2024-01-02T00:00:00Z'},
                    'snippet': {'title': 'Title 2'},
                },
            ]
        }
        mock_channels = MagicMock()
        mock_channels.list.return_value.execute.return_value = {
            'items': [
                {
                    'id': 'channel-1',
                    'snippet': {'title': 'Title Channel'},
                    'contentDetails': {'relatedPlaylists': {'uploads': 'UPLOADS'}}
                }
            ]
        }
        mock_playlist_items = MagicMock()
        mock_playlist_items.list.return_value.execute.return_value = mock_playlist_response

        mock_youtube.channels.return_value = mock_channels
        mock_youtube.playlistItems.return_value = mock_playlist_items

        videos = get_my_videos('test_credentials', 2)
        self.assertEqual(len(videos), 2)
        self.assertEqual(videos[0]['video_id'], 'video1')
        self.assertEqual(videos[0]['title'], 'Title 1')

    def test_list_my_channels(self):
        mock_youtube = MagicMock()
        mock_channels = MagicMock()
        mock_channels.list.return_value.execute.return_value = {
            'items': [
                {
                    'id': 'channel-1',
                    'snippet': {'title': 'Primary'},
                    'contentDetails': {'relatedPlaylists': {'uploads': 'UPLOADS1'}}
                },
                {
                    'id': 'channel-2',
                    'snippet': {'title': 'Brand'},
                    'contentDetails': {'relatedPlaylists': {'uploads': 'UPLOADS2'}}
                },
            ]
        }
        mock_youtube.channels.return_value = mock_channels

        channels = list_my_channels(mock_youtube)

        self.assertEqual(channels[0]['channel_id'], 'channel-1')
        self.assertEqual(channels[1]['uploads_playlist_id'], 'UPLOADS2')

    @patch('src.youtube_private_utils.get_transcript_segments')
    def test_get_transcript(self, mock_get_segments):
        mock_get_segments.return_value = [{'text': 'Hello'}, {'text': 'world'}]

        transcript = get_transcript('test_video_id', service=MagicMock())
        self.assertEqual(transcript, 'Hello world')
        mock_get_segments.assert_called_once()

if __name__ == '__main__':
    unittest.main()
