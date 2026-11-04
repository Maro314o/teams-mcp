import unittest
from unittest.mock import patch
from teams_mcp.files import FilesError, list_team_files, search_team_files

ITEMS=[
 {'type':'file','name':'old.pdf','path':'/old.pdf','modified':'2026-01-01T12:00:00Z','size':2},
 {'type':'folder','name':'folder','path':'/folder','modified':'2027-01-01T00:00:00Z'},
 {'type':'file','name':'recent.pdf','path':'/recent.pdf','modified':'2026-03-01T12:00:00+01:00','size':9},
 {'type':'file','name':'unknown.pdf','path':'/unknown.pdf','modified':None,'size':None},
]

class SortingTests(unittest.TestCase):
 def setUp(self):
  self.site=patch('teams_mcp.files.validate_site',return_value='https://example.sharepoint.com/sites/a');self.site.start();self.addCleanup(self.site.stop)
  self.libs=patch('teams_mcp.files.api_collection',return_value=[{'BaseTemplate':101,'Hidden':False,'Title':'Docs','RootFolder':{'ServerRelativeUrl':'/root'}}]);self.libs.start();self.addCleanup(self.libs.stop)
  walk=patch('teams_mcp.files.walk_folders',return_value=ITEMS);self.walk=walk.start();self.addCleanup(walk.stop)
 def test_default_preserves_order_and_all_items(self):
  r=list_team_files({},'id','site',None)
  self.assertEqual(r['items'],ITEMS)
 def test_sort_then_limit_after_filter(self):
  r=list_team_files({},'id','site',None,sort_by='modified',order='desc',limit=2,item_type='file')
  self.assertEqual([x['name'] for x in r['items']],['recent.pdf','old.pdf'])
  self.assertEqual(r['total_matches'],3);self.assertTrue(r['truncated']);self.assertFalse(r['complete'])
 def test_search_filters_before_limit_and_sort(self):
  r=search_team_files({},'id','site',None,extension='pdf',sort_by='modified',order='desc',limit=1)
  self.assertEqual([x['name'] for x in r['items']],['recent.pdf']);self.assertEqual(r['total_matches'],3)
 def test_invalid_options(self):
  for kwargs in ({'sort_by':'invalid'},{'limit':0},{'limit':True},{'order':'desc'},{'item_type':'unknown'}):
   with self.subTest(kwargs=kwargs),self.assertRaises(FilesError):list_team_files({},'id','site',None,**kwargs)
 def test_missing_dates_sort_last_in_both_directions(self):
  for order in ['asc','desc']:
   r=list_team_files({},'id','site',None,sort_by='modified',order=order,item_type='file')
   self.assertEqual(r['items'][-1]['name'],'unknown.pdf')

class ExtensionFilterTests(SortingTests):
 def test_list_filters_multiple_extensions_before_sort_and_limit(self):
  self.walk.return_value=ITEMS + [{'type':'file','name':'slides.PPTX','path':'/slides.PPTX','modified':'2026-04-01T00:00:00Z'}]
  r=list_team_files({},'id','site',None,sort_by='modified',order='desc',limit=2,extensions=['.PDF','pptx'])
  self.assertEqual([x['name'] for x in r['items']],['slides.PPTX','recent.pdf'])
  self.assertEqual(r['total_matches'],4)
 def test_search_multiple_extensions_combines_with_name(self):
  self.walk.return_value=ITEMS + [{'type':'file','name':'recent.PPTX','path':'/recent.PPTX'}]
  r=search_team_files({},'id','site',None,name='recent',extensions=['pdf','.pptx'])
  self.assertEqual([x['name'] for x in r['items']],['recent.pdf','recent.PPTX'])
 def test_invalid_extension_lists_are_rejected(self):
  for ext in ([],[''],['a/b'],['.'],['a\\b']):
   with self.subTest(ext=ext),self.assertRaises(FilesError): list_team_files({},'id','site',None,extensions=ext)
 def test_incompatible_extension_options_are_rejected(self):
  with self.assertRaises(FilesError): search_team_files({},'id','site',None,extension='pdf',extensions=['pptx'])
  with self.assertRaises(FilesError): list_team_files({},'id','site',None,item_type='folder',extensions=['pdf'])
