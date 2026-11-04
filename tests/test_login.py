import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from teams_mcp.login import save_session

class LoginTests(unittest.TestCase):
    def test_refuses_invalid_session_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'session.json'; path.write_text('previous')
            with patch('teams_mcp.login.check_session', side_effect=ValueError('invalid')):
                with self.assertRaises(ValueError): save_session({'cookies':[]},path)
            self.assertEqual(path.read_text(),'previous')

    def test_save_private_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'private'/'session.json'
            with patch('teams_mcp.login.check_session', return_value='https://example.sharepoint.com'):
                save_session({'cookies':[]},path)
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            self.assertEqual(path.parent.stat().st_mode & 0o777,0o700)
