# Teams MCP

Server MCP locale per elencare i Team visibili nell’interfaccia Teams web con un account Microsoft scolastico. È un primo passo verso la consultazione dei materiali condivisi; non è un client Teams ufficiale.

## Cosa fa

- `get_setup_status`: controlla la sessione con una richiesta SharePoint in sola lettura. Distingue la richiesta di accesso dai problemi di rete e dall'accesso negato.
- `begin_login(site_url)`: apre una finestra Chromium locale sulla radice dell'organizzazione, derivata dall'indirizzo SharePoint indicato. Accedi tu direttamente su Microsoft.
- `complete_login`: dopo il tuo «fatto», acquisisce e verifica la sessione; salva solo se valida. In caso di errore conserva la sessione precedente. La finestra scade dopo 15 minuti.
- `list_teams`: apre Teams web con Playwright in modalità headless e restituisce i Team visualizzati come `name` e `team_id`. Il server gestisce internamente la navigazione. L'identificatore distingue Team omonimi; l’associazione al sito SharePoint è basata sui nomi ed è un’euristica. Se non riesce a riconoscere la vista, restituisce un errore invece di dichiarare che non ci sono Team.

- `list_team_files(team_id, max_depth=None, site_url=None)`: elenca ricorsivamente le raccolte documenti accessibili del sito principale, con nome, tipo, URL SharePoint, dimensione e modifica. `max_depth=0` mostra gli elementi immediati di ciascuna raccolta; omettilo per tutti i livelli. L’associazione automatica confronta il nome Team con i siti cercati e funziona solo con un risultato esatto univoco: è un'euristica, non una prova di identità; in caso di dubbio passa `site_url`. Gli errori per raccolta sono riportati e `complete` è sempre `false`: canali privati/condivisi e contenuti esterni non vengono individuati. L'elenco non è paginato sul lato MCP.

- `search_team_files(team_id, name=None, extension=None, path_contains=None, max_depth=None, site_url=None)`: cerca file nel sito principale applicando almeno un filtro non vuoto. I filtri sono combinati e non distinguono maiuscole; l’estensione accetta sia `pdf` sia `.pdf`. La ricerca visita le raccolte usando la stessa ricorsione di `list_team_files`, non cerca nel contenuto dei documenti e conserva gli stessi limiti ed errori di copertura. La risposta non è paginata.
Per `list_team_files` e `search_team_files` sono disponibili i parametri opzionali `sort_by` (`name`, `modified` o `size`), `order` (`asc` o `desc`; predefinito `asc` quando si ordina) e `limit` (intero positivo). Senza `sort_by` l'ordine di visita non cambia; `order` richiede `sort_by`. `list_team_files` accetta anche `item_type` (`file` o `folder`). Ricerca e filtro precedono l'ordinamento, che precede il limite; i valori di ordinamento mancanti o non validi sono alla fine. La risposta contiene `total_matches`, `returned_count` e `truncated`; per la ricerca `count` indica i risultati restituiti. Questi conteggi riguardano solo gli elementi effettivamente esplorati: la copertura è descritta da `complete`, `errors` e `note`. Il limite riduce l'output ma non abbrevia la scansione, e non è ancora prevista paginazione. L'elenco può includere risorse tecniche del sito.

Entrambi i tool accettano `extensions`, una lista facoltativa di estensioni esatte, per esempio `["pdf", ".docx", "pptx"]`: basta una corrispondenza e maiuscole e punto iniziale sono indifferenti. Il filtro restituisce solo file, non cartelle; non è compatibile con `item_type="folder"`. In ricerca `extension` resta disponibile per una sola estensione, in alternativa a `extensions`. Il filtro è applicato prima di ordinamento e limite, ma non riduce la scansione delle cartelle.

- `download_team_files(team_id, destination_path, site_url=None)`: scarica le raccolte accessibili del sito principale in sottocartelle distinte; non individua automaticamente canali privati/condivisi né contenuti esterni e riporta `complete: false`. La corrispondenza automatica per nome è un’euristica.
- `download_item(source_url, destination_path)`: scarica un file o una cartella SharePoint nel percorso assoluto indicato, ricorsivamente per le cartelle. Non sovrascrive file esistenti e restituisce scaricati, saltati ed errori. Per un file `destination_path` è il nome completo del file; per una cartella è la cartella di destinazione.

## Installazione tramite un agente Codex

Puoi dare all’agente il link di questo repository e scrivere:

> Installa Teams MCP seguendo il README, configura il plugin, la skill e il server MCP locale, poi guidami nel primo accesso Microsoft senza chiedermi password o cookie in chat.

### Istruzioni per l’agente che esegue l’installazione

1. Verifica di lavorare sul computer e sull’account Codex in cui l’utente desidera usare il plugin. L’installazione descritta qui è **locale a quell’host**. Servono Linux con desktop grafico per il login, `git`, `make`, `uv` e Python 3.11 o successivo. Chromium di Playwright viene installato durante la procedura. Se manca un prerequisito, spiega come installarlo seguendo le istruzioni ufficiali; non acquisire password o codici dell’utente.
2. Scegli una cartella di lavoro accessibile all’utente. Se il repository non è già presente, clona `https://github.com/Maro314o/teams-mcp.git` e apri la cartella `teams-mcp`. Se esiste già, controlla remoto e stato Git e preserva le modifiche locali; non sovrascrivere né azzerare un checkout esistente.
3. Controlla `codex plugin marketplace list --json`, `codex plugin list --json` e `codex mcp list --json`. Per una **prima installazione**, dalla radice del checkout esegui:

   ```sh
   make install-local-plugin
   ```

   Il comando sincronizza `.venv` con `uv.lock`, installa Chromium di Playwright, registra il marketplace locale `teams-mcp-repo`, installa il plugin e la skill `teams-mcp`, e registra il server `teams-mcp` in Codex usando il percorso assoluto del checkout. Il server viene avviato in locale su stdio. Il comando registra anche le variabili grafiche presenti nella sessione: eseguilo dal desktop dove l’utente farà login.
4. Se plugin o server sono già installati, verifica prima i loro percorsi e la loro origine. Non rimuovere o sovrascrivere configurazioni esistenti di altri progetti né ripetere alla cieca il comando di prima installazione. Questo repository non fornisce ancora un comando di aggiornamento automatico: comunica all’utente la situazione e intervieni sulla sola installazione Teams MCP appropriata.
5. Verifica che il plugin `teams-mcp@teams-mcp-repo` sia abilitato e che `codex mcp list --json` riporti il server `teams-mcp` abilitato con il percorso dell’eseguibile `.venv/bin/teams-mcp` del checkout. Esegui anche `uv run --locked python -m unittest discover -s tests`. Poi chiedi all’utente di aprire **una nuova chat locale**: i tool e le skill di una chat già avviata non si ricaricano automaticamente. Non dichiarare che i tool siano disponibili nella nuova chat finché non sono stati verificati lì.
6. Nella nuova chat, prima di accedere ai dati, chiama `get_setup_status`. Se serve autenticarsi, chiedi solo un URL SharePoint dell’organizzazione, se non è già noto; chiama `begin_login` e lascia che l’utente acceda a Microsoft nella finestra del browser. Quando conferma «fatto», chiama `complete_login` e verifica nuovamente `get_setup_status`. Se Teams richiede un accesso separato, spiegalo: il login SharePoint potrebbe non bastare. Non chiedere né stampare password, codici, cookie o token; non aprire o sostituire la sessione esistente per un semplice controllo.

Il login salva la sessione localmente fuori dal repository. Una sessione valida SharePoint non garantisce automaticamente l’accesso a Teams; verificare i tool senza inventare risultati. Le funzionalità e i limiti di copertura dei file sono descritti sopra.

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
