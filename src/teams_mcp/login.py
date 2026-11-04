"""Accesso interattivo e salvataggio privato della sessione."""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
from teams_mcp.session import session_path
from teams_mcp.sharepoint import check_session, normalize_origin

_job = None

def save_session(data, target=None):
    check_session(data)
    target=target or session_path()
    directory=target.parent
    directory.mkdir(mode=0o700,parents=True,exist_ok=True)
    info=directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise PermissionError('Cartella sessione non sicura')
    os.chmod(directory,0o700)
    fd,tmp=tempfile.mkstemp(prefix='.session-',dir=directory)
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,'w',encoding='utf8') as f:
            json.dump(data,f); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,target)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def begin_login(site_url):
    global _job
    origin=normalize_origin(site_url)
    if _job and _job[0].poll() is None: return {'status':'in_progress','message':'Finestra già aperta; completa il login e poi usa complete_login.'}
    if _job:
        import shutil
        shutil.rmtree(_job[1],ignore_errors=True)
    directory=Path(tempfile.mkdtemp(prefix='teams-mcp-login-'))
    process=subprocess.Popen([sys.executable,'-m','teams_mcp.login','worker',origin,str(directory)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
    _job=(process,directory)
    return {'status':'in_progress','message':'Apertura browser avviata. Accedi a SharePoint e poi chiedi di completare il login.'}

def complete_login():
    global _job
    if not _job: return {'status':'not_started','message':'Avvia prima la procedura di login.'}
    process,directory=_job
    if process.poll() is None: (directory/'finish').touch(mode=0o600)
    try: process.wait(timeout=30)
    except subprocess.TimeoutExpired: return {'status':'in_progress','message':'Verifica ancora in corso; riprova.'}
    try:
        result=json.loads((directory/'result.json').read_text())
    except (OSError,ValueError): result={'status':'error','message':'Impossibile avviare il browser o completare il login. Verifica che Chromium Playwright sia installato e che sia disponibile un desktop.'}
    import shutil
    shutil.rmtree(directory,ignore_errors=True)
    _job=None
    return result

def worker(origin,directory):
    from playwright.sync_api import sync_playwright
    result={'status':'error','message':'Login non completato o sessione non verificabile; sessione precedente conservata.'}
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=False)
            context=browser.new_context()
            page=context.new_page()
            page.goto(origin,wait_until='domcontentloaded',timeout=60000)
            deadline=time.monotonic()+900
            while time.monotonic()<deadline and not (directory/'finish').exists(): page.wait_for_timeout(500)
            if (directory/'finish').exists():
                data=context.storage_state()
                if not any(c.get('domain','').lstrip('.').lower()==origin.removeprefix('https://') for c in data.get('cookies',[])):
                    raise ValueError('Tenant errato')
                save_session(data)
                result={'status':'ready','message':'Sessione verificata e salvata.'}
            browser.close()
    except Exception:
        pass
    (directory/'result.json').write_text(json.dumps(result),encoding='utf8')

if __name__=='__main__' and len(sys.argv)==4 and sys.argv[1]=='worker':
    worker(sys.argv[2],Path(sys.argv[3]))
