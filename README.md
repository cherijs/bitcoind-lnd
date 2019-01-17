## Bitcoind + LND setup for testnet
Docker setup to create bictoind and LND containers work together, to create Lightning network.

* Edit `bitcoind/bitcoin.conf` and `lnd/lnd.conf` with your settings and just `docker-compose up -d` should work

* If you'd like to stop just one of the services (btc or lnd containers), use `docker-compose stop lnd` and then use the command `docker-compose up -d --build lnd` to start it again

* If you've made changes to any of the files and need to rebuild just one of the containers, use `docker-compose up -d --build lnd`

## After blockchain is synced
After containers are started for the first time, let btc sync with blockchain (that may take a while ~27GB for testnet). After that you need:

* create lightning wallet with command `docker-compose exec lnd lncli -n=testnet create`

* Unlock walet use command `docker-compose exec lnd lncli -n=testnet unlock`