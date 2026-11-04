import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from teams_mcp.download import download_team_files

class TeamDownloadTests(unittest.TestCase):
 def test_libraries_use_distinct_subdirectories_and_report_scope(self):
  libs=[{'Title':'Documenti','BaseTemplate':101,'Hidden':False,'RootFolder':{'ServerRelativeUrl':'/sites/a/Documents'}},{'Title':'Materiale','BaseTemplate':101,'Hidden':False,'RootFolder':{'ServerRelativeUrl':'/sites/a/Materiale'}}]
  with tempfile.TemporaryDirectory() as d, patch('teams_mcp.download.resolve_site',return_value='https://example.sharepoint.com/sites/a'),patch('teams_mcp.download.api_collection',return_value=libs),patch('teams_mcp.download.download_item',return_value={'downloaded':['one'],'skipped':[],'errors':[],'complete':True}) as call:
   r=download_team_files({},'team',d,None)
   self.assertFalse(r['complete'])
   self.assertEqual(len(r['libraries']),2)
   self.assertEqual({Path(x.args[2]).name for x in call.call_args_list},{'Documenti','Materiale'})
