"""Individuazione prudente e visita delle raccolte SharePoint."""
from datetime import datetime, timezone
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



def validate_selection(sort_by, order, limit, item_type=None):
    if sort_by not in (None, 'name', 'modified', 'size'):
        raise FilesError('invalid_sort', 'sort_by deve essere name, modified o size.')
    if order not in (None, 'asc', 'desc') or (order is not None and sort_by is None):
        raise FilesError('invalid_sort', 'order richiede sort_by e deve essere asc o desc.')
    if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 1):
        raise FilesError('invalid_limit', 'limit deve essere un intero positivo.')
    if item_type not in (None, 'file', 'folder'):
        raise FilesError('invalid_type', 'item_type deve essere file o folder.')


def select_items(result, sort_by=None, order=None, limit=None, item_type=None):
    validate_selection(sort_by, order, limit, item_type)
    items = [item for item in result['items'] if item_type is None or item.get('type') == item_type]
    if sort_by:
        def value(item):
            raw = item.get(sort_by)
            if raw is None: return None
            if sort_by == 'name': return raw.casefold() if isinstance(raw, str) else None
            if sort_by == 'size': return raw if isinstance(raw, (int, float)) and not isinstance(raw, bool) else None
            try:
                date = datetime.fromisoformat(raw.replace('Z', '+00:00'))
                return date.timestamp() if date.tzinfo else date.replace(tzinfo=timezone.utc).timestamp()
            except (ValueError, TypeError, OverflowError, OSError): return None
        known = [(item, value(item)) for item in items]
        missing = [item for item, key in known if key is None]
        valid = [(item, key) for item, key in known if key is not None]
        valid.sort(key=lambda pair: pair[0].get('path', ''))
        valid.sort(key=lambda pair: pair[1], reverse=order == 'desc')
        items = [item for item, _ in valid] + missing
    total = len(items)
    if limit is not None: items = items[:limit]
    return {**result, 'items': items, 'total_matches': total, 'returned_count': len(items), 'truncated': len(items) < total}

def normalize_extensions(extensions):
    if extensions is None: return None
    if not isinstance(extensions, list) or not extensions:
        raise FilesError('invalid_extension', 'Specifica una lista non vuota di estensioni.')
    normalized = []
    for extension in extensions:
        if not isinstance(extension, str):
            raise FilesError('invalid_extension', 'Ogni estensione deve essere una stringa.')
        value = extension.strip().casefold().removeprefix('.')
        if not value or any(c in value for c in '/\\.') or any(c.isspace() for c in value):
            raise FilesError('invalid_extension', 'Specifica estensioni semplici, per esempio pdf o .docx.')
        normalized.append(value)
    return normalized

def matches_extension(item, extensions):
    return item.get('type') == 'file' and any(item['name'].casefold().endswith('.' + ext) for ext in extensions)

def list_team_files(session,team_id,site_url,max_depth,sort_by=None,order=None,limit=None,item_type=None,extensions=None):
    validate_selection(sort_by,order,limit,item_type)
    extensions=normalize_extensions(extensions)
    if extensions and item_type == 'folder':
        raise FilesError('invalid_type', 'Il filtro estensioni si applica solo ai file.')
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
    result={'site_url':site,'items':items,'errors':errors,'complete':False,'note':'Esplorate le raccolte accessibili del sito indicato; canali privati/condivisi e contenuti esterni non sono individuati automaticamente.'}
    if extensions: result['items']=[item for item in result['items'] if matches_extension(item,extensions)]
    return select_items(result,sort_by,order,limit,item_type)


def search_team_files(session, team_id, site_url, max_depth, name=None, extension=None, path_contains=None, sort_by=None, order=None, limit=None, extensions=None):
    validate_selection(sort_by,order,limit)
    """Filtra i file dell'elenco ricorsivo; preserva gli avvisi sulla copertura."""
    name = name.strip().casefold() if name else None
    if extension and extensions is not None:
        raise FilesError('invalid_extension', 'Usa extension oppure extensions, non entrambi.')
    extensions = normalize_extensions(extensions if extensions is not None else ([extension] if extension else None))
    path_contains = path_contains.strip().casefold() if path_contains else None
    if not any((name, extensions, path_contains)):
        raise FilesError('invalid_search', 'Specifica almeno un filtro non vuoto: nome, estensione o percorso.')
    result = list_team_files(session, team_id, site_url, max_depth)
    matches = []
    for item in result['items']:
        if item.get('type') != 'file':
            continue
        item_name = item['name'].casefold()
        if name and name not in item_name:
            continue
        if extensions and not matches_extension(item, extensions):
            continue
        if path_contains and path_contains not in item.get('path', '').casefold():
            continue
        matches.append(item)
    selected = select_items({**result, 'items': matches},sort_by,order,limit)
    return {**selected, 'count': len(selected['items'])}
