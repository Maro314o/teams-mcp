import unittest
from unittest.mock import Mock, patch
from teams_mcp.sharepoint import SharePointError, check_response, extract_sites, normalize_origin

class SharePointTests(unittest.TestCase):
    def test_validate_host(self):
        self.assertEqual(normalize_origin('https://example.sharepoint.com/sites/abc'), 'https://example.sharepoint.com')
        for value in ('http://example.sharepoint.com','https://sharepoint.com.evil.org','https://u:p@example.sharepoint.com'):
            with self.assertRaises(ValueError): normalize_origin(value)

    def test_session_error_classification(self):
        for status, expected in [(401,'login_required'),(403,'access_denied'),(500,'service_error')]:
            response=Mock(status_code=status, headers={})
            with self.assertRaises(SharePointError) as e: check_response(response)
            self.assertEqual(e.exception.code, expected)

    def test_search_maps_names_and_urls_and_filters_external(self):
        rows=[{'Cells':[{'Key':'Title','Value':'Classe A'},{'Key':'Path','Value':'https://example.sharepoint.com/sites/a'}]}, {'Cells':[{'Key':'Title','Value':'Bad'},{'Key':'Path','Value':'https://evil.example/path'}]}]
        self.assertEqual(extract_sites(rows,'https://example.sharepoint.com'),[{'name':'Classe A','site_url':'https://example.sharepoint.com/sites/a'}])
