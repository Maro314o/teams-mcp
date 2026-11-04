# Sessione e ricerca siti SharePoint

- Gestire sessione privata fuori dal repository, login in browser gestito dal server e completamento esplicito; non sostituire la sessione esistente se la verifica fallisce.
- Verificare l'accesso tramite currentuser, distinguendo sessione non valida, accesso negato ed errore di rete.
- Cercare siti SharePoint accessibili, restituendo titolo e URL stabile; la ricerca non equivale all'elenco dei Team e potrebbe essere incompleta.
- Esporre gli strumenti su MCP stdio, aggiungere istruzioni operative e testare unità, protocollo e servizio reale senza divulgare credenziali.
