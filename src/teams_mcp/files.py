"""Individuazione prudente e visita delle raccolte SharePoint."""
from urllib.parse import quote, urlsplit, urlunsplit
from teams_mcp.sharepoint import SharePointError, get_origin, list_sites, call, normalize_origin
from teams_mcp.teams import fetch_teams

class FilesError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code=code


def validate_site(session, site_url):
    origin=get_origin(session)
    parsed=urlsplit(site_url)
    if normalize_origin(site_url)!=origin or not parsed.path.lower().startswith('/sites/') or parsed.query or parsed.fragment:
        raise FilesError('invalid_site','Indica l’URL del sito SharePoint della tua organizzazione.')
    return urlunsplit(('https',parsed.netloc,parsed.path.rstrip('/'),'',''))


def resolve_site(session, team_id):
    matches=[x for x in fetch_teams(session) if x['team_id']==team_id]
    if len(matches)!=1: raise FilesError('team_not_found','Team non trovato nella vista Teams.')
    sites=list_sites(session)['sites']
    candidates=[s['site_url'] for s in sites if s['name'].casefold()==matches[0]['name'].casefold()]
    if len(candidates)!=1:
        raise FilesError('site_ambiguous','Non posso associare il Team a un sito in modo univoco. Specifica site_url.')
    return validate_site(session,candidates[0])


def api_collection(session,site,endpoint,params=None):
    origin=get_origin(session); site_path=urlsplit(site).path
    response=call(origin,site_path+endpoint,session,params)
    rows=[]
    while True:
        if not isinstance(response,dict) or not isinstance(response.get('value'),list):
            raise FilesError('unexpected_response','Risposta SharePoint non riconosciuta.')
        rows.extend(response['value'])
        next_url=response.get('odata.nextLink') or response.get('@odata.nextLink')
        if not next_url: return rows
        p=urlsplit(next_url)
        if normalize_origin(next_url)!=origin or not p.path.startswith(site_path+'/_api/'):
            raise FilesError('unexpected_response','Paginazione SharePoint non valida.')
        response=call(origin,p.path+'?'+p.query,session)


def folder_entries(session,site,path):
    base='/_api/web/GetFolderByServerRelativePath(decodedurl=@p)'
    params={'@p':"'"+path.replace("'","''")+"'",'$select':'Name,ServerRelativeUrl,TimeLastModified,Length'}
    folders=api_collection(session,site,base+'/Folders',{'@p':params['@p'],'$select':'Name,ServerRelativeUrl,TimeLastModified'})
    files=api_collection(session,site,base+'/Files',params)
    return ([{'name':x['Name'],'path':x['ServerRelativeUrl'],'modified':x.get('TimeLastModified')} for x in folders], [{'name':x['Name'],'path':x['ServerRelativeUrl'],'size':int(x['Length']) if x.get('Length') is not None else None,'modified':x.get('TimeLastModified')} for x in files])


def walk_folders(session,site,root,max_depth):
    if max_depth is not None and (isinstance(max_depth,bool) or not isinstance(max_depth,int) or max_depth<0): raise FilesError('invalid_depth','max_depth deve essere un intero maggiore o uguale a zero.')
    result=[]; stack=[(root,0)]; visited=set()
    while stack:
        path,depth=stack.pop()
        if path in visited: continue
        visited.add(path)
        folders,files=folder_entries(session,site,path)
        for item in folders: result.append({'type':'folder',**item,'sharepoint_url':normalize_origin(site)+quote(item['path'],safe='/')})
        for item in files: result.append({'type':'file',**item,'sharepoint_url':normalize_origin(site)+quote(item['path'],safe='/')})
        if max_depth is None or depth<max_depth:
            stack.extend((item['path'],depth+1) for item in reversed(folders))
    return result


def list_team_files(session,team_id,site_url,max_depth):
    if max_depth is not None and (isinstance(max_depth,bool) or not isinstance(max_depth,int) or max_depth<0): raise FilesError('invalid_depth','max_depth deve essere un intero maggiore o uguale a zero.')
    site=validate_site(session,site_url) if site_url else resolve_site(session,team_id)
    lists=api_collection(session,site,'/_api/web/lists',{'$select':'Title,BaseTemplate,Hidden,RootFolder/ServerRelativeUrl','$expand':'RootFolder'})
    libraries=[x for x in lists if x.get('BaseTemplate')==101 and not x.get('Hidden')]
    items=[]; errors=[]
    for library in libraries:
        root=library.get('RootFolder',{}).get('ServerRelativeUrl')
        if not root: errors.append({'library':library.get('Title'),'error':'Percorso non disponibile'}); continue
        try: items.extend(walk_folders(session,site,root,max_depth))
        except (FilesError,SharePointError,KeyError,ValueError): errors.append({'library':library.get('Title'),'error':'Impossibile elencare completamente la raccolta'})
    return {'site_url':site,'items':items,'errors':errors,'complete':False,'note':'Esplorate le raccolte accessibili del sito indicato; canali privati/condivisi e contenuti esterni non sono individuati automaticamente.'}


def search_team_files(session, team_id, site_url, max_depth, name=None, extension=None, path_contains=None):
    """Filtra i file dell'elenco ricorsivo; preserva gli avvisi sulla copertura."""
    name = name.strip().casefold() if name else None
    extension = extension.strip().casefold().lstrip('.') if extension else None
    path_contains = path_contains.strip().casefold() if path_contains else None
    if not any((name, extension, path_contains)):
        raise FilesError('invalid_search', 'Specifica almeno un filtro non vuoto: nome, estensione o percorso.')
    if extension and ('/' in extension or '\\' in extension):
        raise FilesError('invalid_search', 'L’estensione non può contenere separatori di percorso.')
    result = list_team_files(session, team_id, site_url, max_depth)
    matches = []
    for item in result['items']:
        if item.get('type') != 'file':
            continue
        item_name = item['name'].casefold()
        if name and name not in item_name:
            continue
        if extension and not item_name.endswith('.' + extension):
            continue
        if path_contains and path_contains not in item.get('path', '').casefold():
            continue
        matches.append(item)
    return {**result, 'items': matches, 'count': len(matches)}
