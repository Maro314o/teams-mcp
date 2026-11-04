"""Legge i Team visualizzati da Teams web in un browser locale headless."""
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout, Error as PlaywrightError

CARD_SELECTOR = '[data-tid$="-team-card"]'

class TeamsError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def parse_cards(cards):
    if not cards:
        raise TeamsError('teams_view_unavailable', 'Nessuna scheda Team riconosciuta; la vista potrebbe essere vuota, incompleta o cambiata.')
    result=[]
    seen=set()
    for card in cards:
        tid=card.get('tid') or ''
        names=card.get('names') or []
        if not tid.endswith('-team-card') or len(names)!=1 or not names[0].strip():
            raise TeamsError('teams_view_unavailable', 'Struttura della scheda Teams non riconosciuta.')
        team_id=tid.removesuffix('-team-card')
        if team_id not in seen:
            result.append({'name': names[0].strip(), 'team_id': team_id})
            seen.add(team_id)
    return result


def fetch_teams(session):
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            try:
                context=browser.new_context(storage_state=session)
                page=context.new_page()
                page.goto('https://teams.microsoft.com/', wait_until='domcontentloaded', timeout=45000)
                try:
                    page.locator(CARD_SELECTOR).first.wait_for(state='visible', timeout=50000)
                except PlaywrightTimeout as exc:
                    host=(urlsplit(page.url).hostname or '').lower()
                    if host in ('login.microsoftonline.com','login.microsoft.com'):
                        raise TeamsError('teams_login_required', 'Teams richiede un nuovo accesso nel browser; la sessione SharePoint potrebbe essere ancora valida.') from exc
                    raise TeamsError('teams_view_unavailable', 'Impossibile riconoscere la lista Team: potrebbe non essersi caricata o essere cambiata.') from exc
                # Attendere che il numero di schede rimanga stabile per consentire il caricamento delle sezioni.
                last=-1
                stable=0
                for _ in range(20):
                    count=page.locator(CARD_SELECTOR).count()
                    stable=stable+1 if count==last else 0
                    if stable>=4: break
                    last=count
                    page.wait_for_timeout(1000)
                else:
                    raise TeamsError('teams_view_unavailable','La lista Team non ha terminato il caricamento.')
                cards=page.locator(CARD_SELECTOR).evaluate_all("elements => elements.map(e => ({tid: e.getAttribute('data-tid'), names: [...e.querySelectorAll('span[dir=auto]')].map(n => n.innerText)}))")
                return parse_cards(cards)
            finally:
                browser.close()
    except TeamsError:
        raise
    except PlaywrightError as exc:
        raise TeamsError('browser_error','Impossibile aprire Teams nel browser headless. Verifica la rete e Chromium Playwright.') from exc
