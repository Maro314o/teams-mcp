import unittest
from unittest.mock import patch
from teams_mcp.files import walk_folders, resolve_site, FilesError

class FileListingTests(unittest.TestCase):
 def test_walk_depth_and_metadata(self):
  tree={'/root':([{'name':'A','path':'/root/A'}],[{'name':'one.txt','path':'/root/one.txt','size':7,'modified':'today'}]),'/root/A':([],[{'name':'two','path':'/root/A/two','size':2,'modified':'today'}])}
  with patch('teams_mcp.files.folder_entries',side_effect=lambda s,u,p:tree[p]):
   shallow=walk_folders({},'https://example.sharepoint.com/sites/class','/root',0)
   self.assertEqual([x['name'] for x in shallow],['A','one.txt'])
   deep=walk_folders({},'https://example.sharepoint.com/sites/class','/root',None)
   self.assertEqual([x['name'] for x in deep],['A','one.txt','two'])
   self.assertEqual(deep[1]['size'],7)

 def test_ambiguous_names_require_explicit_site(self):
  with patch('teams_mcp.files.fetch_teams',return_value=[{'name':'Math','team_id':'id'}]), patch('teams_mcp.files.list_sites',return_value={'sites':[{'name':'Math','site_url':'https://example.sharepoint.com/sites/a'},{'name':'Math','site_url':'https://example.sharepoint.com/sites/b'}]}):
   with self.assertRaises(FilesError): resolve_site({},'id')
