import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from teams_mcp.session import session_path, session_status


class SessionTests(unittest.TestCase):
    def test_default_path_is_outside_project(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'XDG_DATA_HOME': temp}):
            self.assertEqual(session_path(), Path(temp) / 'teams-mcp' / 'session.json')

    def test_status_reports_only_presence(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'XDG_DATA_HOME': temp}):
            self.assertEqual(session_status(), {'configured': False})
            session_path().parent.mkdir()
            session_path().write_text('{"secret":"private"}')
            self.assertEqual(session_status(), {'configured': True})

if __name__ == '__main__':
    unittest.main()
