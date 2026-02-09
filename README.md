# pool_bitcoin_unique_best

Pool de minage SHA256d avec service web multi-utilisateurs et serveur Stratum TCP.

## Fonctionnalités
- Inscription/connexion multi-utilisateurs via interface web.
- Connexion RPC à Bitcoin Core (sans rapporter le hash rate).
- Serveur Stratum TCP (par défaut: `stratum+tcp://bac.elit21.pool:3333`).

## Configuration
Variables d'environnement utiles:

- `BITCOIN_RPC_HOST` (par défaut `127.0.0.1`)
- `BITCOIN_RPC_PORT` (par défaut `8332`)
- `BITCOIN_RPC_USER`
- `BITCOIN_RPC_PASSWORD`
- `STRATUM_HOST` (par défaut `0.0.0.0`)
- `STRATUM_PORT` (par défaut `3333`)
- `POOL_SECRET_KEY`

## Lancer le service web

```bash
python app.py
```

## Lancer le serveur Stratum

```bash
python stratum_server.py
```

Le serveur Stratum n'utilise pas `getnetworkhashps` afin d'éviter d'influencer la difficulté réseau.

## Commandes RPC utiles pour le pool (Blockchain)
Liste triée et réduite aux appels nécessaires pour suivre l'état de la chaîne et des blocs:

- `getbestblockhash`
- `getblock "blockhash" ( verbosity )`
- `getblockchaininfo`
- `getblockcount`
- `getblockhash height`
- `getblockheader "blockhash" ( verbose )`
- `getdifficulty`

## Commandes RPC utilisées par le pool (Stratum)
Les appels suivants sont utilisés pour alimenter l'état du pool et valider les blocs,
sans déclarer de hash rate auprès de Bitcoin Core:

- `getbestblockhash`
- `getblockheader "blockhash" ( verbose )`
- `getdifficulty`
- `getblocktemplate "template_request"`
- `getprioritisedtransactions`
- `submitblock "hexdata" ( dummy )`
- `submitheader "hexdata"`
- `testblockvalidity "block_hex"`
