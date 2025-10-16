import unittest
from unittest.mock import patch, MagicMock
from src.youtube_private_utils import (
    get_authenticated_service,
    get_user_credentials,
    get_authorization_url,
    get_my_videos,
    get_transcript,
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

        mock_search_response = {
            'items': [
                {'id': {'videoId': 'video1'}, 'snippet': {'title': 'Title 1', 'publishedAt': '2024-01-01T00:00:00Z'}},
                {'id': {'videoId': 'video2'}, 'snippet': {'title': 'Title 2', 'publishedAt': '2024-01-02T00:00:00Z'}},
            ]
        }
        mock_youtube.search.return_value.list.return_value.execute.return_value = mock_search_response

        videos = get_my_videos('test_credentials', 2)
        self.assertEqual(len(videos), 2)
        self.assertEqual(videos[0]['video_id'], 'video1')
        self.assertEqual(videos[0]['title'], 'Title 1')

    @patch('src.youtube_private_utils.get_transcript_segments')
    def test_get_transcript(self, mock_get_segments):
        mock_get_segments.return_value = [{'text': 'Hello'}, {'text': 'world'}]

        transcript = get_transcript('test_video_id', service=MagicMock())
        self.assertEqual(transcript, 'Hello world')
        mock_get_segments.assert_called_once()

if __name__ == '__main__':
    unittest.main()
