from flask_testing import TestCase
import unittest
from app import app
from unittest.mock import patch


class TestAPIs(TestCase):
    def create_app(self):
        app.config['TESTING'] = True
        return app

    # Mocking the APIVerification class
    @patch('app.APIVerification')
    def test_process_api(self, mock_APIVerification):
        # Creating a mock object of APIVerification
        mock_api_verification = mock_APIVerification.return_value
        mock_api_verification.verify_request.return_value = True

        # Mocking the 'getAfterCount' method of 'db' object
        with patch('app.db.getAfterCount') as mock_get_after_count:
            mock_get_after_count.return_value = {"_id": "123", "Key": "api_key", "Url": "http://example.com"}

            # Mocking 'requests' module
            with patch('app.requests') as mock_requests:
                mock_requests.request.return_value.ok = True

                # Mocking 'collection' function
                with patch('app.collection') as mock_collection:
                    mock_collection.return_value.put.return_value = None

                    # Sending a GET request
                    response = self.client.get('/api/v1/')
                    self.assertEqual(response.status_code, 200)

    # Add more tests...


if __name__ == "__main__":
    unittest.main()
