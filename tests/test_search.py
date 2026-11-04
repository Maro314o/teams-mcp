import asyncio
import unittest
from unittest.mock import patch
from teams_mcp.files import FilesError, search_team_files
from teams_mcp.server import search_team_files as search_tool

ITEMS = [
    {'type':'file','name':'Integrali.PDF','path':'/Matematica/Lezioni/Integrali.PDF','size':10},
    {'type':'file','name':'Esercizi.pdf','path':'/Matematica/Esercizi/Esercizi.pdf','size':20},
    {'type':'file','name':'Lezione.txt','path':'/Matematica/Lezioni/Lezione.txt','size':2},
    {'type':'folder','name':'PDF','path':'/Matematica/PDF'},
]

class SearchTests(unittest.TestCase):
    @patch('teams_mcp.files.list_team_files')
    def test_combines_filters_case_insensitively_and_preserves_coverage(self, listing):
        listing.return_value={'site_url':'https://example.sharepoint.com/sites/a','items':ITEMS,'errors':[{'library':'private'}],'complete':False,'note':'partial'}
        result=search_team_files({},'id','https://example.sharepoint.com/sites/a',2,name='integrali',extension='pdf',path_contains='LEZIONI')
        self.assertEqual([i['name'] for i in result['items']],['Integrali.PDF'])
        self.assertEqual(result['errors'],[{'library':'private'}])
        self.assertFalse(result['complete'])
        listing.assert_called_once_with({},'id','https://example.sharepoint.com/sites/a',2)

    @patch('teams_mcp.files.list_team_files')
    def test_empty_filters_are_rejected_before_listing(self, listing):
        with self.assertRaises(FilesError): search_team_files({},'id',None,None,name='  ')
        listing.assert_not_called()

    @patch('teams_mcp.files.list_team_files')
    def test_directories_not_returned_and_dot_extension_supported(self, listing):
        listing.return_value={'items':ITEMS,'errors':[],'complete':False}
        result=search_team_files({},'id',None,None,extension='.PDF')
        self.assertEqual([i['name'] for i in result['items']],['Integrali.PDF','Esercizi.pdf'])

    @patch('teams_mcp.server.search_files',return_value={'items':[],'errors':[],'complete':False})
    @patch('teams_mcp.server.load_session',return_value={})
    @patch('teams_mcp.server.session_path')
    def test_tool_passes_filters_to_server(self,path,load,search):
        path.return_value.is_file.return_value=True
        result=asyncio.run(search_tool('id',name='esercizi',max_depth=1))
        self.assertEqual(result['status'],'ready')
        search.assert_called_once_with({},'id',None,1,'esercizi',None,None,None,None,None,None)
