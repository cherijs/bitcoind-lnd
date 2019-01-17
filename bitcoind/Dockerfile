FROM alpine

ARG VERSION=0.17.1
ARG GLIBC_VERSION=2.27-r0

ENV FILENAME bitcoin-${VERSION}-x86_64-linux-gnu.tar.gz
ENV DOWNLOAD_URL https://bitcoin.org/bin/bitcoin-core-${VERSION}/${FILENAME}

RUN apk update \
  && apk --no-cache add wget tar bash ca-certificates \
  && wget -q -O /etc/apk/keys/sgerrand.rsa.pub https://alpine-pkgs.sgerrand.com/sgerrand.rsa.pub \
  && wget https://github.com/sgerrand/alpine-pkg-glibc/releases/download/${GLIBC_VERSION}/glibc-${GLIBC_VERSION}.apk \
  && wget https://github.com/sgerrand/alpine-pkg-glibc/releases/download/${GLIBC_VERSION}/glibc-bin-${GLIBC_VERSION}.apk \
  && apk --no-cache add glibc-${GLIBC_VERSION}.apk \
  && apk --no-cache add glibc-bin-${GLIBC_VERSION}.apk \
  && rm -rf /glibc-${GLIBC_VERSION}.apk \
  && rm -rf /glibc-bin-${GLIBC_VERSION}.apk \
  && wget $DOWNLOAD_URL \
  && tar xzvf /bitcoin-${VERSION}-x86_64-linux-gnu.tar.gz \
  && mkdir /root/.bitcoin \
  && mv /bitcoin-${VERSION}/bin/* /usr/local/bin/ \
  && rm -rf /bitcoin-${VERSION}/ \
  && rm -rf /bitcoin-${VERSION}-x86_64-linux-gnu.tar.gz \
  && apk del tar wget ca-certificates

EXPOSE 8333 18333 18332 28333 28332

CMD bitcoind -conf=/root/.bitcoin/bitcoin.conf -datadir=/root/.bitcoin -printtoconsole
