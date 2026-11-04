"""Download di file e cartelle SharePoint senza sovrascrittura."""
import os
import secrets
from pathlib import Path
from urllib.parse import unquote, urlsplit
import requests
from teams_mcp.files import folder_entries, FilesError
from teams_mcp.sharepoint import cookie_jar, get_origin, normalize_origin, check_response

class DownloadError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code=code


def remote_location(session, url):
    origin=get_origin(session)
    try:
        p=urlsplit(url)
        path=unquote(p.path)
        if normalize_origin(url)!=origin or p.query or p.fragment or '\\' in path or '\x00' in path: raise ValueError()
        parts=path.split('/')
        if len(parts)<4 or parts[1].lower()!='sites' or not parts[2] or any(x in ('.','..') for x in parts): raise ValueError()
    except ValueError:
        raise DownloadError('invalid_url','Usa un URL completo del sito SharePoint della tua organizzazione, senza parametri.')
    return origin, '/'+ '/'.join(parts[1:3]),path


def open_directory(path,create=False):
    path=Path(path)
    if not path.is_absolute() or '..' in path.parts: raise DownloadError('invalid_destination','La destinazione deve essere un percorso assoluto senza ..')
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            if create:
                try: os.mkdir(part,0o700,dir_fd=fd)
                except FileExistsError: pass
            next_fd=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            os.close(fd);fd=next_fd
        return fd
    except BaseException:
        os.close(fd);raise


def safe_write(destination,chunks):
    destination=Path(destination)
    if destination.name in ('','.','..'): raise DownloadError('invalid_destination','Nome del file non valido.')
    fd=open_directory(destination.parent,create=True)
    temporary='.teams-mcp-'+secrets.token_hex(12)
    try:
        f=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
        try:
            with os.fdopen(f,'wb') as stream:
                for chunk in chunks:
                    if chunk: stream.write(chunk)
            os.link(temporary,destination.name,src_dir_fd=fd,dst_dir_fd=fd,follow_symlinks=False)
        finally:
            try:os.unlink(temporary,dir_fd=fd)
            except FileNotFoundError:pass
    finally:os.close(fd)


def request_resource(session, origin, site_path, kind, remote_path, content=False):
    parameter="'"+remote_path.replace("'","''")+"'"
    endpoint='/_api/web/Get'+kind+'ByServerRelativePath(decodedurl=@p)'+('/$value' if content else '')
    try:
        return requests.get(origin+site_path+endpoint,params={'@p':parameter},cookies=cookie_jar(session,origin),headers={'Accept':'application/json;odata=nometadata'},allow_redirects=False,timeout=(15,60),stream=content)
    except requests.RequestException as exc: raise DownloadError('network_error','SharePoint non raggiungibile.') from exc


def download_item(session, source_url, destination):
    origin,site_path,remote_path=remote_location(session,source_url)
    dest=Path(destination)
    if not dest.is_absolute() or '..' in dest.parts: raise DownloadError('invalid_destination','Usa un percorso locale assoluto senza ..')
    site=origin+site_path
    probe=request_resource(session,origin,site_path,'Folder',remote_path)
    try: status=probe.status_code
    finally: probe.close()
    if status==200:
        fd=open_directory(dest,create=True);os.close(fd)
        downloaded=[];skipped=[];errors=[];stack=[(remote_path,dest)]
        while stack:
            remote,local=stack.pop()
            try: folders,files=folder_entries(session,site,remote)
            except Exception: errors.append({'path':remote,'error':'Impossibile elencare la cartella'});continue
            for item in folders:
                name=item['name']
                if name in ('.','..') or '/' in name or '\\' in name: errors.append({'path':item['path'],'error':'Nome non valido'});continue
                try:
                    directory=local/name; fd=open_directory(directory,create=True);os.close(fd);stack.append((item['path'],directory))
                except OSError: errors.append({'path':item['path'],'error':'Impossibile creare cartella locale'})
            for item in files:
                name=item['name']
                if name in ('.','..') or '/' in name or '\\' in name:errors.append({'path':item['path'],'error':'Nome non valido'});continue
                try: download_file(session,origin,site_path,item['path'],local/name);downloaded.append(str(local/name))
                except FileExistsError: skipped.append(str(local/name))
                except (OSError,DownloadError,requests.RequestException):errors.append({'path':item['path'],'error':'Download non riuscito'})
        return {'type':'folder','downloaded':downloaded,'skipped':skipped,'errors':errors,'complete':not errors and not skipped}
    if status!=404:
        check_response(probe)
        raise DownloadError('unexpected_response','Risposta imprevista durante il controllo della cartella.')
    try: download_file(session,origin,site_path,remote_path,dest)
    except FileExistsError: return {'type':'file','downloaded':[],'skipped':[str(dest)],'errors':[],'complete':False}
    return {'type':'file','downloaded':[str(dest)],'skipped':[],'errors':[],'complete':True}


def download_file(session,origin,site_path,path,destination):
    response=request_resource(session,origin,site_path,'File',path,content=True)
    try:
        check_response(response)
        safe_write(destination,response.iter_content(chunk_size=65536))
    finally:response.close()
