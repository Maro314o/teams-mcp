"""Server MCP locale per la ricerca di siti SharePoint accessibili."""
import asyncio
from mcp.server.fastmcp import FastMCP
from teams_mcp.login import begin_login as start_login, complete_login as finish_login
from teams_mcp.session import session_path
from teams_mcp.sharepoint import SharePointError, check_session, load_session
from teams_mcp.teams import TeamsError, fetch_teams

mcp=FastMCP('teams-mcp')

def _error(exc):
    if isinstance(exc, (SharePointError, TeamsError)): return {'status':exc.code,'message':str(exc)}
    return {'status':'session_error','message':'Sessione locale non leggibile o non valida. Ripeti il login.'}

@mcp.tool()
def get_setup_status() -> dict:
    """Verifica la sessione con una richiesta SharePoint leggera; non restituisce credenziali."""
    if not session_path().is_file(): return {'status':'login_required','configured':False}
    try:
        check_session(load_session())
        return {'status':'ready','configured':True}
    except (SharePointError,ValueError,OSError,KeyError,TypeError) as exc: return _error(exc)

@mcp.tool()
def begin_login(site_url: str) -> dict:
    """Apre un browser locale. site_url è un URL HTTPS SharePoint della propria organizzazione."""
    try: return start_login(site_url)
    except (ValueError,OSError) as exc: return {'status':'error','message':str(exc)}

@mcp.tool()
def complete_login() -> dict:
    """Da chiamare dopo che l'utente ha completato il login nella finestra del browser."""
    return finish_login()

@mcp.tool()
async def list_teams() -> dict:
    """Elenca i Team mostrati in Teams web tramite browser headless. Restituisce nome e identificatore Team."""
    if not session_path().is_file(): return {'status':'login_required','message':'Avvia begin_login con l’indirizzo SharePoint della scuola.'}
    try: return {'status':'ready','teams':await asyncio.to_thread(fetch_teams, load_session())}
    except (TeamsError,SharePointError,ValueError,OSError,KeyError,TypeError) as exc: return _error(exc)

def main(): mcp.run(transport='stdio')
if __name__=='__main__': main()
