"""Operazioni SharePoint in sola lettura."""
import json
from urllib.parse import urlsplit
import requests
from teams_mcp.session import session_path

class SharePointError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code

def normalize_origin(value):
    p = urlsplit(value)
    host = p.hostname or ''
    if p.scheme != 'https' or not host.endswith('.sharepoint.com') or host == '.sharepoint.com' or p.username or p.password or p.port not in (None,443):
        raise ValueError('Serve un indirizzo HTTPS SharePoint valido.')
    return 'https://' + host.lower()

def load_session(path=None):
    with (path or session_path()).open(encoding='utf8') as f:
        return json.load(f)

def get_origin(data):
    candidates = sorted({c.get('domain','').lstrip('.').lower() for c in data.get('cookies', []) if c.get('name','').lower() in ('fedauth','rtfa') and c.get('domain','').lstrip('.').lower().endswith('.sharepoint.com') and not c.get('domain','').lstrip('.').lower().endswith('-my.sharepoint.com')})
    if len(candidates) != 1: raise SharePointError('configuration_required','Indirizzo SharePoint non determinabile dalla sessione.')
    return normalize_origin('https://' + candidates[0])

def cookie_jar(data, origin):
    host=urlsplit(origin).hostname
    jar=requests.cookies.RequestsCookieJar()
    for c in data.get('cookies', []):
        domain=c.get('domain','').lstrip('.').lower()
        if c.get('name','').lower() in ('fedauth','rtfa','spoidcrl') and (host == domain or host.endswith('.'+domain)):
            jar.set(c['name'],c['value'],domain=c['domain'],path=c.get('path','/'))
    return jar

def check_response(response):
    status=response.status_code
    if status == 401 or 300 <= status < 400: raise SharePointError('login_required','Sessione scaduta o autenticazione richiesta.')
    if status == 403: raise SharePointError('access_denied','Accesso negato: la sessione potrebbe essere valida, ma questo sito non è accessibile.')
    if status != 200: raise SharePointError('service_error',f'SharePoint ha risposto con HTTP {status}.')

def call(origin, endpoint, data, params=None):
    try:
        r=requests.get(origin+endpoint,params=params,cookies=cookie_jar(data,origin),headers={'Accept':'application/json;odata=nometadata'},allow_redirects=False,timeout=15)
    except requests.RequestException as exc:
        raise SharePointError('network_error','SharePoint non raggiungibile; riprova.') from exc
    check_response(r)
    try: return r.json()
    except ValueError as exc: raise SharePointError('unexpected_response','Risposta SharePoint inattesa.') from exc

def check_session(data):
    origin=get_origin(data)
    result=call(origin,'/_api/web/currentuser',data,{'$select':'Id'})
    if not isinstance(result.get('Id'), int): raise SharePointError('unexpected_response','Risposta di accesso non riconosciuta.')
    return origin

def extract_sites(rows, origin):
    result=[]
    for row in rows:
        cells={c.get('Key'):c.get('Value') for c in row.get('Cells', [])}
        url=cells.get('Path') or ''
        try:
            p=urlsplit(url)
            if normalize_origin(url)!=origin or p.query or p.fragment: continue
        except ValueError: continue
        if cells.get('Title') and urlsplit(url).path.lower().startswith('/sites/'):
            result.append({'name':cells['Title'],'site_url':url})
    return result

def list_sites(data):
    origin=check_session(data)
    payload=call(origin,'/_api/search/query',data,{'querytext':"'contentclass:STS_Site OR contentclass:STS_Web'",'selectproperties':"'Title,Path'",'rowlimit':'100','trimduplicates':'false'})
    try:
        relevant=payload['PrimaryQueryResult']['RelevantResults']
        return {'sites':extract_sites(relevant['Table']['Rows'],origin),'total_results':relevant['TotalRows'],'limit':100,'note':'Risultati della ricerca SharePoint: non tutti sono necessariamente Team; i risultati possono essere incompleti.'}
    except (KeyError,TypeError) as exc: raise SharePointError('unexpected_response','Risposta della ricerca non riconosciuta.') from exc
