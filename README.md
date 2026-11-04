# Teams MCP

Server MCP locale per elencare i Team visibili nell’interfaccia Teams web con un account Microsoft scolastico. È un primo passo verso la consultazione dei materiali condivisi; non è un client Teams ufficiale.

## Cosa fa

- `get_setup_status`: controlla la sessione con una richiesta SharePoint in sola lettura. Distingue la richiesta di accesso dai problemi di rete e dall'accesso negato.
- `begin_login(site_url)`: apre una finestra Chromium locale sulla radice dell'organizzazione, derivata dall'indirizzo SharePoint indicato. Accedi tu direttamente su Microsoft.
- `complete_login`: dopo il tuo «fatto», acquisisce e verifica la sessione; salva solo se valida. In caso di errore conserva la sessione precedente. La finestra scade dopo 15 minuti.
- `list_teams`: apre Teams web con Playwright in modalità headless e restituisce i Team visualizzati come `name` e `team_id`. Il server gestisce internamente la navigazione. L'identificatore distingue Team omonimi; l’associazione al sito SharePoint è basata sui nomi ed è un’euristica. Se non riesce a riconoscere la vista, restituisce un errore invece di dichiarare che non ci sono Team.

- `list_team_files(team_id, max_depth=None, site_url=None)`: elenca ricorsivamente le raccolte documenti accessibili del sito principale, con nome, tipo, URL SharePoint, dimensione e modifica. `max_depth=0` mostra gli elementi immediati di ciascuna raccolta; omettilo per tutti i livelli. L’associazione automatica confronta il nome Team con i siti cercati e funziona solo con un risultato esatto univoco: è un'euristica, non una prova di identità; in caso di dubbio passa `site_url`. Gli errori per raccolta sono riportati e `complete` è sempre `false`: canali privati/condivisi e contenuti esterni non vengono individuati. L'elenco non è paginato sul lato MCP.

- `download_team_files(team_id, destination_path, site_url=None)`: scarica le raccolte accessibili del sito principale in sottocartelle distinte; non individua automaticamente canali privati/condivisi né contenuti esterni e riporta `complete: false`. La corrispondenza automatica per nome è un’euristica.
- `download_item(source_url, destination_path)`: scarica un file o una cartella SharePoint nel percorso assoluto indicato, ricorsivamente per le cartelle. Non sovrascrive file esistenti e restituisce scaricati, saltati ed errori. Per un file `destination_path` è il nome completo del file; per una cartella è la cartella di destinazione.

## Installazione e avvio

Richiede Python 3.11+, [uv](https://docs.astral.sh/uv/) e una sessione desktop Linux per il login.

```sh
uv sync --locked
uv run playwright install chromium
uv run teams-mcp
```

Il server usa `stdio`: attende messaggi MCP e non apre una porta per il protocollo. Configura il client MCP con il percorso assoluto di `.venv/bin/teams-mcp` come comando e `stdio` come trasporto. Il plugin contiene la skill; il server viene registrato separatamente nel Codex locale con un percorso assoluto, come per ClasseViva. Per una prima installazione esegui `make install-local-plugin` e apri una nuova chat. Se il server è già registrato, non ripetere il comando senza prima verificare la configurazione esistente.

Se il client MCP non trasmette le variabili grafiche al processo, configurare almeno `DISPLAY` (e, se necessario, `WAYLAND_DISPLAY` e `XDG_RUNTIME_DIR`) nell’ambiente del server MCP: senza accesso al desktop la finestra di login non può aprirsi. Il valore corretto dipende dalla sessione desktop; non impostarlo a un valore fisso per tutti gli utenti.

La prima volta l'agente chiede un indirizzo SharePoint dell'organizzazione, apre la finestra del browser con `begin_login` e attende che tu acceda. Scrivi «fatto» solo quando la pagina SharePoint si è aperta. L'agente chiama `complete_login` e riprova l'operazione. Le credenziali non vanno scritte in chat. Il browser si apre sul desktop e può richiedere nuovamente l'accesso dopo la scadenza della sessione.

## Sessione e sicurezza

Su Linux la sessione è salvata in `$XDG_DATA_HOME/teams-mcp/session.json`, oppure `~/.local/share/teams-mcp/session.json`. Il browser viene controllato dal programma, senza leggere profili personali esistenti. Prima di sostituire il file il programma verifica che la nuova sessione acceda a SharePoint; scrive un file temporaneo privato e lo sostituisce atomicamente. La cartella viene creata con permessi `0700`, il file con `0600` e viene verificato il proprietario della cartella. I segreti non sono restituiti dagli strumenti MCP. La sessione corrente rimane intatta se il nuovo login non va a buon fine.

Il file può contenere cookie e token utilizzabili come l'utente. I permessi Unix non cifrano i dati e non proteggono da processi dello stesso account o dall'amministratore. Non condividerlo né inserirlo in Git; `.gitignore` esclude i file di sessione comuni. Rimuovere il file elimina solo la copia locale; per revocare l'accesso usare anche le funzioni Microsoft. La durata della sessione dipende dalla scuola e dalle politiche Microsoft.

Le richieste API SharePoint usano il solo tenant `*.sharepoint.com` ricavato dalla sessione e non seguono redirect. Per listare i Team il browser apre anche Teams e i normali servizi Microsoft di autenticazione. La lettura della vista Teams non è un’integrazione Microsoft Graph ufficiale e può interrompersi se l’interfaccia cambia. Se Teams richiede un login separato, il login attuale su SharePoint potrebbe non essere sufficiente.

## Verifica

```sh
uv run --locked python -m unittest discover -s tests
```

## Sviluppo

Il progetto usa `uv` per ambiente, dipendenze e lockfile. La [guida allo sviluppo](docs/sviluppo.md) descrive i componenti e i comandi; [AGENTS.md](AGENTS.md) contiene le istruzioni per gli agenti che lavorano sul repository. La skill in `skills/teams-setup/` è destinata invece agli agenti che usano il server.
