# Istruzioni per lo sviluppo di Teams MCP

Questo file è per gli agenti che **sviluppano il repository**. La skill `skills/teams-setup/SKILL.md` è invece destinata agli agenti che **usano** il server per rispondere all'utente; non confondere le due funzioni.

## Prima di modificare

- Leggi `README.md` e `docs/sviluppo.md`, quindi i file e i test pertinenti alla richiesta. Rispetta le modifiche già presenti e non azzerare il repository.
- Il progetto usa `uv`: gestisci dipendenze con `uv add` / `uv remove` e includi le modifiche a `pyproject.toml` e `uv.lock`. Non creare un secondo ambiente o un file requirements parallelo senza una ragione specifica.
- Esegui i comandi del progetto con `uv run --locked`; se si modificano le dipendenze, aggiorna prima il lockfile con `uv`.

## Architettura e comportamento

- `src/teams_mcp/server.py` espone i tool MCP su stdio; stdout è riservato al protocollo. `teams.py` interroga la vista Teams tramite Playwright headless; `sharepoint.py` contiene operazioni SharePoint; `login.py` gestisce la finestra di login e la scrittura della sessione; `session.py` determina il percorso locale.
- `list_teams` deriva i risultati dall'interfaccia Teams, non dall'elenco dei siti SharePoint. I selettori non sono un'API ufficiale e possono cambiare. Mantieni distinti errore di rete, autenticazione e vista non riconosciuta; non presentare un errore come elenco vuoto.
- `team_id` è l'identificatore ricavato dalla vista Teams. Non assumere che sia già un URL o l'identificativo di un sito SharePoint; l'associazione al sito per nome univoco è solo un'euristica e non garantisce l'identità del Team.
- Il login usa un browser controllato dal programma. L'utente inserisce i dati direttamente su Microsoft. Non richiedere, stampare, registrare o trasferire in chat password, token, cookie o il contenuto della sessione. Non aprire profili personali del browser.
- La sessione è esterna al repository, in `$XDG_DATA_HOME/teams-mcp/session.json` oppure `~/.local/share/teams-mcp/session.json`. Non eliminarla, sovrascriverla o revocarla durante test o installazione. Usa sessioni e cartelle temporanee fittizie nei test; per prove reali usa solo ciò che l'utente autorizza e non esporre dati riservati.
- Mantieni la distinzione tra l'esistenza di una sessione, la sua validità SharePoint e l'effettivo accesso a Teams. La sessione SharePoint può essere valida mentre Teams richiede un nuovo login.

## Verifica e integrazione

- Esegui almeno `uv lock --check` e `uv run --locked python -m unittest discover -s tests`; aggiungi verifiche mirate quando servono. Per modifiche al trasporto verifica anche una vera inizializzazione e una chiamata MCP; non affermare che un flusso browser o una nuova chat funzioni se non è stato verificato.
- Se modifichi un tool o il suo comportamento, aggiorna README e skill dell'utente. Se modifichi l'identità o i metadati del plugin, mantieni coerenti `plugin.json` e `.codex-plugin/plugin.json`.
- Il plugin installato e il server registrato in Codex sono distinti. Il server punta all'ambiente locale del checkout; la skill installata è una copia e potrebbe richiedere reinstallazione. Verifica lo stato prima di modificare l'installazione e non eliminare altri plugin o configurazioni.
- Per aggiornare o installare componenti globali, browser o dipendenze, rispetta le autorizzazioni della sessione. Non fare commit o pubblicazioni se non richiesti.
