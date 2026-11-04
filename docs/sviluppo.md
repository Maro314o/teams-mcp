# Guida allo sviluppo

## Ambiente uv

Il repository è un progetto `uv`: `pyproject.toml` descrive il pacchetto e le dipendenze, `uv.lock` ne registra la risoluzione e `.venv/` è l'ambiente locale generato, escluso da Git. Richiede Python 3.11 o successivo e `uv`.

```sh
uv sync --locked
uv run --locked playwright install chromium
uv run --locked python -m unittest discover -s tests
uv lock --check
```

L'installazione del browser scarica componenti esterni; è necessaria per login e consultazione di Teams, non per tutti i test unitari. Per avviare il server in un client MCP, usa l'entry point `uv run --locked teams-mcp`; il processo comunica su stdio e resta in attesa di richieste. Non inviare output diagnostico su stdout.

Per aggiungere o rimuovere dipendenze usa `uv add NOME` o `uv remove NOME` e includi il lockfile aggiornato nelle modifiche. `uv sync --locked` e `uv run --locked` verificano che il lockfile sia coerente, senza aggiornarlo silenziosamente. L'ambiente è installato in modalità modificabile da `uv`, quindi le modifiche al sorgente sono visibili senza reinstallare il pacchetto; cambiamenti alle dipendenze richiedono la sincronizzazione.

## Componenti

- `server.py`: tool MCP, avvio stdio e risposta agli errori.
- `teams.py`: browser headless e interpretazione delle schede della vista Teams. È un'integrazione con l'interfaccia web, non l'API ufficiale Graph.
- `sharepoint.py`: sessione e chiamate SharePoint; distingue ricerca siti e Team.
- `files.py`: individuazione delle raccolte, visita ricorsiva e ricerca per nome, estensione e percorso nel sito principale; ordinamento e limite si applicano dopo l’esplorazione e i filtri.
- `download.py`: download di file, cartelle e raccolte, senza sovrascrittura.
- `login.py`: processo del browser interattivo e salvataggio della sessione dopo verifica SharePoint.
- `session.py`: percorso della sessione locale.
- `skills/teams-setup/SKILL.md`: istruzioni per l'agente che usa il server.
- `tests/`: test unitari senza credenziali reali. `AGENTS.md` contiene indicazioni per gli agenti che sviluppano.

La lista Teams può fallire se la pagina cambia, non termina il caricamento o richiede un accesso separato. Il server elenca e scarica raccolte del sito principale; l’associazione `team_id`-sito per nome univoco è un’euristica, non una prova di identità. I canali privati o condivisi e i contenuti esterni non sono automaticamente coperti.

## Sviluppo del plugin locale

Il server registrato globalmente in Codex e il plugin con la skill sono componenti distinti. Il server configurato con il percorso `.venv/bin/teams-mcp` dipende dall'ambiente del checkout. Il plugin usa una copia della skill installata nel marketplace locale; aggiornarne il sorgente non garantisce che la copia installata si aggiorni da sola. Dopo aggiornamenti alla registrazione o alla skill, verificare plugin e server con `codex plugin list` e `codex mcp list`, poi usare una nuova chat per caricare gli strumenti. La procedura di prima installazione è descritta nel README; verificare la configurazione esistente prima di ripeterla.

## Dati di sessione

Tratta `session.json` come una credenziale. Il percorso effettivo usa `XDG_DATA_HOME` se assoluto, altrimenti `~/.local/share/teams-mcp/`. La scrittura attuale controlla che la cartella appartenga all'utente, imposta permessi `0700`/`0600`, verifica la sessione SharePoint e sostituisce atomicamente il file. Questi permessi non cifrano i dati e non proteggono da processi dello stesso utente. Non salvare sessioni reali nel repository, nei fixture, nei log o nei report dei test.
