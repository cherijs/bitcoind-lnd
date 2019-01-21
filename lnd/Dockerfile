FROM golang:1.11-alpine as builder


ENV GODEBUG netdns=cgo
ENV GOPATH=/go
ENV PATH=$PATH:$GOPATH/bin

# BUG - make fails if this env ins not 0
# https://github.com/golang/go/issues/26988
ENV CGO_ENABLED=0 

RUN apk add --no-cache git make

RUN go get -d github.com/lightningnetwork/lnd && cd $GOPATH/src/github.com/lightningnetwork/lnd && make &&  make install

FROM alpine

EXPOSE 9735 10009

COPY --from=builder /go/bin/lncli /bin/
COPY --from=builder /go/bin/lnd /bin/

RUN apk add --no-cache bash

CMD ["--debuglevel=debug", "--maxpendingchannels=10", "--rpclisten=0.0.0.0:10009", "--color=#4126a7", "--alias=MDMA", "--bitcoin.active", "--bitcoin.testnet", "--bitcoin.node=bitcoind", "--bitcoind.rpchost=btc", "--bitcoind.rpcuser=test", "--bitcoind.rpcpass=test", "--bitcoind.zmqpubrawblock=tcp://btc:28332", "--bitcoind.zmqpubrawtx=tcp://btc:28333", "--autopilot.active", "--autopilot.maxchannels=5", "--autopilot.allocation=0.6"]
ENTRYPOINT ["lnd"]