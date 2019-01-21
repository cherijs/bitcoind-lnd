# Regtest

`docker-compose up -d`

then restart lnd container, because btc container now is initialised and lnd now can connect to btc
```bash
docker-compose restart lnd
```

##### Connect to lnd
```bash
docker exec -i -t lnd bash
```

##### check wallet ballance

$lnd `lncli -n=regtest walletbalance`

```json
{
    "total_balance": "0",
    "confirmed_balance": "0",
    "unconfirmed_balance": "0"
}
```

##### get wallet address
$lnd `lncli -n=regtest newaddress np2wkh`
```json
{
    "address": "2NC4FMaJmgoXF6EPodAwokdEeMxFnNgerom"
}
```

### Connect to btc

In new terminal window
```bash
docker exec -i -t btc bash
```

##### check balance

$btc `bitcoin-cli getwalletinfo`

### Mine some bitcoins
generate 400 blocks

$btc `bitcoin-cli generate 400`

##### check balance
$btc `bitcoin-cli getwalletinfo`

### Send bitcoin to LN wallet

$btc `bitcoin-cli sendtoaddress 2NC4FMaJmgoXF6EPodAwokdEeMxFnNgerom 1 "My first Bitcoin"`

##### Check LN wallet balance in lnd terminal

$lnd `lncli -n=regtest walletbalance`
```json
{
    "total_balance": "100000000",
    "confirmed_balance": "0",
    "unconfirmed_balance": "100000000"
}
```

##### Generate 1 bock on btc

$btc `bitcoin-cli generate 1`

##### Check LN wallet balance

$lnd `lncli -n=regtest walletbalance`
```json
{
    "total_balance": "100000000",
    "confirmed_balance": "100000000",
    "unconfirmed_balance": "0"
}
```

So we have a bitcoin in our LN wallet, lets open some channels..
Or first create two more lnd nodes - Alice and Bob

```bash
docker-compose -f docker-compose.yaml -f docker-compose-alice.yaml run -d --name alice -p 10010:10009 -p 9010:9735 lnd
docker-compose -f docker-compose.yaml -f docker-compose-bob.yaml run -d --name bob -p 10011:10009 -p 9011:9735 lnd
```

##### Alice

New terminal

`docker exec -i -t alice bash`

$bob `lncli -n=regtest walletbalance`

$bob `lncli -n=regtest newaddress np2wkh`

copy bobs Alices address

##### BTC container

$btc `bitcoin-cli sendtoaddress ALICE_ADDRESS 1 "Alices first Bitcoin"`

$btc `bitcoin-cli generate 1`

$bob `lncli -n=regtest walletbalance`

Now Bob have 1 bitcoin ;)

##### Bob

New terminal

`docker exec -i -t bob bash`

$bob `lncli -n=regtest walletbalance`

$bob `lncli -n=regtest newaddress np2wkh`

copy Bobs btc address

##### BTC container

$btc `bitcoin-cli sendtoaddress BOBS_ADDRESS 1 "Bobs first Bitcoin"`

$btc `bitcoin-cli generate 1`

$bob `lncli -n=regtest walletbalance`

Now Alice have 1 bitcoin ;)


## We have 3 lnd nodes lnd | bob | alice
Now we can make channels...
----




# Bitcoind + LND setup for testnet
Find replace all regtest -> testnet in docker-compose and lnd.conf, bitcoin.conf files

Docker setup to create bictoind and LND containers work together, to create Lightning network.

* Edit `bitcoind/bitcoin.conf` and `lnd/lnd.conf` with your settings and just `docker-compose up -d` should work

* If you'd like to stop just one of the services (btc or lnd containers), use `docker-compose stop lnd` and then use the command `docker-compose up -d --build lnd` to start it again

* If you've made changes to any of the files and need to rebuild just one of the containers, use `docker-compose up -d --build lnd`

## After blockchain is synced
After containers are started for the first time, let btc sync with blockchain (that may take a while ~27GB for testnet). After that you need:

* create lightning wallet with command `docker-compose exec lnd lncli -n=testnet create`

* Unlock walet use command `docker-compose exec lnd lncli -n=testnet unlock`