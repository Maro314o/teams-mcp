import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from teams_mcp.download import safe_write, remote_location, DownloadError

class DownloadTests(unittest.TestCase):
 def test_no_overwrite(self):
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'file';f.write_bytes(b'old')
   with self.assertRaises(FileExistsError): safe_write(f,[b'new'])
   self.assertEqual(f.read_bytes(),b'old')

 def test_symlink_parent_refused(self):
  with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as other:
   p=Path(d)/'link';p.symlink_to(other,target_is_directory=True)
   with self.assertRaises((OSError,DownloadError)): safe_write(p/'file',[b'secret'])
   self.assertFalse((Path(other)/'file').exists())

 def test_reject_different_tenant_and_traversal(self):
  with patch('teams_mcp.download.get_origin',return_value='https://example.sharepoint.com'):
   for url in ['https://evil.sharepoint.com/sites/a/file','https://example.sharepoint.com/sites/a/%2e%2e/file','https://example.sharepoint.com/sites/a/file?token=abc']:
    with self.assertRaises(DownloadError): remote_location({},url)

class FolderDownloadTests(unittest.TestCase):
 def test_recursive_folder_preserves_existing_files(self):
  from teams_mcp.download import download_item
  class Response:
   status_code=200
   def close(self): pass
  tree={'/sites/a/library':([{'name':'sub','path':'/sites/a/library/sub'}],[{'name':'old.txt','path':'/sites/a/library/old.txt'}]),'/sites/a/library/sub':([],[{'name':'new.txt','path':'/sites/a/library/sub/new.txt'}])}
  def copy(session,origin,site,path,dest): safe_write(dest,[b'new'])
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'out';root.mkdir();(root/'old.txt').write_text('old')
   with patch('teams_mcp.download.remote_location',return_value=('https://example.sharepoint.com','/sites/a','/sites/a/library')), patch('teams_mcp.download.request_resource',return_value=Response()),patch('teams_mcp.download.folder_entries',side_effect=lambda s,site,path:tree[path]),patch('teams_mcp.download.download_file',side_effect=copy):
    result=download_item({},'https://example.sharepoint.com/sites/a/library',str(root))
   self.assertEqual((root/'old.txt').read_text(),'old')
   self.assertEqual((root/'sub'/'new.txt').read_bytes(),b'new')
   self.assertEqual(len(result['skipped']),1)
   self.assertFalse(result['complete'])
