---
name: teams-setup
description: Usa il plugin Teams per richieste naturali sui Team scolastici, sulle materie e sui materiali condivisi in Teams o SharePoint, anche senza nominarlo; guida l'accesso e dichiara i limiti degli strumenti disponibili.
---

# Teams e materiali scolastici

Quando l'utente chiede di vedere i propri Team o un Team di una materia, ad esempio «guardami il Teams di matematica», usa il server MCP locale `teams-mcp` anche se non nomina il plugin. Prima controlla `get_setup_status`. Se `ready`, chiama `list_teams` e individua i Team pertinenti dal nome. Il server legge la vista Teams con un browser headless e restituisce nomi e identificatori. Se i nomi sono ambigui, presenta le alternative usando `team_id` per distinguerle. La navigazione è interna al server: non lanciare browser o script separati per elencare i Team.

Se l’utente vuole l’elenco dei file, usa `list_team_files` con `team_id` e, solo se necessario, `site_url` esplicitamente scelto. L’associazione per nome univoco è un’euristica: non garantisce l’identità del sito. Ometti `max_depth` per tutti i livelli. Segnala sempre che canali separati e contenuti esterni non sono coperti e riporta eventuali errori. Per scaricare un file o una cartella usa `download_item` con `source_url` e un percorso locale assoluto richiesto o concordato con l’utente. Il tool non sovrascrive file esistenti e riporta errori e file saltati. Non sostenere di aver aperto o controllato i file, non inventare contenuti e non aggirare il limite con strumenti non autorizzati. L’elenco dei Team non equivale all’accesso ai file.

Se i tool non sono disponibili, verifica che il plugin sia abilitato e il server registrato con `codex plugin list` e `codex mcp list`. Segui il README del checkout per installare o aggiornare, poi apri una nuova chat: i tool di una chat esistente non vengono ricaricati automaticamente. Non fingere di aver consultato Teams.

## Login

Se lo stato è `login_required`, chiedi l'indirizzo HTTPS SharePoint dell'organizzazione solo se non è già noto. Chiama `begin_login` con `site_url`, spiega che deve accedere nella finestra del browser sul desktop e chiedi di scrivere «fatto». Dopo la conferma chiama `complete_login`; se riesce, ricontrolla `get_setup_status` e prosegui con la richiesta originale. Se il browser non si apre, segui la sezione diagnostica del README. Non chiedere o riportare password, codici, cookie o token.

Se il tool restituisce `teams_login_required`, spiega che Teams richiede un accesso separato; l’attuale login del server apre SharePoint e potrebbe non bastare. Se `teams_view_unavailable` o `browser_error`, segnala il problema senza presentare una lista vuota come risultato.

Se lo stato è `access_denied`, `network_error`, `service_error` o `unexpected_response`, non presumere che la sessione sia scaduta: spiega l'errore. La presenza di un file non prova che la sessione sia valida.
