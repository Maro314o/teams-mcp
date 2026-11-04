import asyncio
import unittest
from unittest.mock import MagicMock, patch
from teams_mcp.teams import parse_cards, TeamsError
from teams_mcp.server import list_teams

class TeamsTests(unittest.TestCase):
    def test_cards_preserve_duplicate_names_and_stable_ids(self):
        cards=[{'tid':'19:alpha@thread.tacv2-team-card','names':['Matematica']}, {'tid':'19:beta@thread.tacv2-team-card','names':['Matematica']}]
        self.assertEqual(parse_cards(cards),[{'name':'Matematica','team_id':'19:alpha@thread.tacv2'}, {'name':'Matematica','team_id':'19:beta@thread.tacv2'}])

    def test_unrecognized_cards_are_not_silently_ignored(self):
        with self.assertRaises(TeamsError): parse_cards([{'tid':'unknown','names':[]}])

    def test_empty_view_is_not_assumed_to_mean_no_teams(self):
        with self.assertRaises(TeamsError): parse_cards([])

    @patch('teams_mcp.server.fetch_teams', return_value=[{'name':'Math','team_id':'id'}])
    @patch('teams_mcp.server.load_session', return_value={'cookies':[]})
    @patch('teams_mcp.server.session_path')
    def test_mcp_delegates_extraction_to_server(self, path, load, fetch):
        path.return_value.is_file.return_value=True
        self.assertEqual(asyncio.run(list_teams()),{'status':'ready','teams':[{'name':'Math','team_id':'id'}]})
