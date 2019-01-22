import codecs
import logging
import os

import grpc

import rpc_pb2 as ln
import rpc_pb2_grpc as lnrpc

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s', )
logger = logging.getLogger('main')

FAUCET_DOCKER = {
    'name': 'FAUCET',
    'node_host': 'localhost:9009',
    'rpc_host': 'localhost:10009',
    'tls_cert': '/Users/cherijs/.docker_volumes/.lnd/tls.cert',
    'admin_macaroon': '/Users/cherijs/.docker_volumes/.lnd/data/chain/bitcoin/regtest/admin.macaroon'
}

ALICE_DOCKER = {
    'name': 'Alice',
    'node_host': 'localhost:9010',
    'rpc_host': 'localhost:10010',
    'tls_cert': '/Users/cherijs/.docker_volumes/simnet/alice/tls.cert',
    'admin_macaroon': '/Users/cherijs/.docker_volumes/simnet/alice/data/chain/bitcoin/regtest/admin.macaroon'
}

BOB_DOCKER = {
    'name': 'Bob',
    'node_host': 'localhost:9011',
    'rpc_host': 'localhost:10011',
    'tls_cert': '/Users/cherijs/.docker_volumes/simnet/bob/tls.cert',
    'admin_macaroon': '/Users/cherijs/.docker_volumes/simnet/bob/data/chain/bitcoin/regtest/admin.macaroon'
}


class RpcClient(object):
    identity_pubkey = None

    def __repr__(self):
        return self.displayName

    def __init__(self, config):
        self.displayName = config['name']

        with open(config['tls_cert'], 'rb') as tls_cert_file:
            cert_credentials = grpc.ssl_channel_credentials(tls_cert_file.read())

            if config['admin_macaroon']:
                with open(config['admin_macaroon'], 'rb') as macaroon_file:
                    macaroon = codecs.encode(macaroon_file.read(), 'hex')
                    macaroon_credentials = self.get_macaroon_credentials(macaroon)
                    credentials = grpc.composite_channel_credentials(cert_credentials, macaroon_credentials)
            else:
                credentials = cert_credentials

            channel = grpc.secure_channel(config["rpc_host"], credentials)

            # Due to updated ECDSA generated tls.cert we need to let gprc know that
            # we need to use that cipher suite otherwise there will be a handhsake
            # error when we communicate with the lnd rpc server.
            os.environ["GRPC_SSL_CIPHER_SUITES"] = 'HIGH+ECDSA'

            logger.info(f'CONNECTING TO {config["name"]}: {config["rpc_host"]}')

            self.client = lnrpc.LightningStub(channel)

            self.identity_pubkey = self.getinfo().identity_pubkey

    @staticmethod
    def get_macaroon_credentials(macaroon):

        def metadata_callback(context, callback):
            # for more info see grpc docs
            callback([("macaroon", macaroon)], None)

        return grpc.metadata_call_credentials(metadata_callback)

    def ping(self):
        try:
            self.client.GetInfo(ln.GetInfoRequest())
            return True
        except Exception as e:
            logger.exception(e)
            return False

    def list_peers(self):
        try:
            peers = self.client.ListPeers(ln.ListPeersRequest()).peers
            return [p.pub_key for p in peers]
        except Exception as e:
            logger.exception(e)
            return []

    def getinfo(self):
        try:
            response = self.client.GetInfo(ln.GetInfoRequest())
            return response
        except Exception as e:
            logger.exception(e)

    def getnode_info(self, pubkey):
        try:
            response = self.client.GetNodeInfo(ln.NodeInfoRequest(pub_key=pubkey))
            return response
        except Exception as e:
            logger.exception(e)

    def wallet_balance(self):
        try:
            response = self.client.WalletBalance(ln.WalletBalanceRequest())
            return {
                'node': self.displayName,
                'total_balance': response.total_balance,
                'confirmed_balance': response.confirmed_balance,
                'unconfirmed_balance': response.unconfirmed_balance,
            }
        except Exception as e:
            logger.exception(e)

    def list_channels(self):
        try:
            response = self.client.ListChannels(ln.ListChannelsRequest())
            return response
        except Exception as e:
            logger.exception(e)

    def list_pending_channels(self):
        try:
            response = self.client.PendingChannels(ln.PendingChannelsRequest())
            return response
        except Exception as e:
            logger.exception(e)

    def channel_exists_with_node(self, pubkey, pending=True):
        connected_channel_list = list(self.list_channels().channels)
        connected_pub_keys = set(ch.remote_pubkey for ch in connected_channel_list)
        pub_keys = connected_pub_keys

        if pending:
            pending_channels_list = list(self.list_pending_channels().pending_open_channels)
            pending_pub_keys = set(chan.channel.remote_node_pub for chan in pending_channels_list)
            pub_keys = pub_keys | pending_pub_keys

        return pubkey in pub_keys

    def add_invoice(self, memo='Pay me', ammount=0, expiry=3600):
        try:
            invoice_req = ln.Invoice(memo=memo, value=ammount, expiry=expiry)
            response = self.client.AddInvoice(invoice_req)
            return response
        except Exception as e:
            logger.exception(e)

    def list_invoices(self):
        try:
            response = self.client.ListInvoices(ln.ListInvoiceRequest())
            return response
        except Exception as e:
            logger.exception(e)

    def decode_pay_request(self, pay_req):
        try:
            pay_req = pay_req.rstrip()
            raw_invoice = ln.PayReqString(pay_req=str(pay_req))
            response = self.client.DecodePayReq(raw_invoice)
            return response
        except Exception as e:
            logger.exception(e)

    def send_payment(self, pay_req):
        invoice_details = self.decode_pay_request(pay_req)
        try:
            request = ln.SendRequest(
                dest_string=invoice_details.destination,
                amt=invoice_details.num_satoshis,
                payment_hash_string=invoice_details.payment_hash,
                final_cltv_delta=144  # final_cltv_delta=144 is default for lnd
            )
            response = self.client.SendPaymentSync(request)
            logger.warning(response)
        except Exception as e:
            logger.exception(e)

    def pay_invoice(self, pay_req):
        invoice_details = self.decode_pay_request(pay_req)
        try:
            request = ln.SendRequest(
                dest_string=invoice_details.destination,
                amt=invoice_details.num_satoshis,
                payment_hash_string=invoice_details.payment_hash,
                final_cltv_delta=144  # final_cltv_delta=144 is default for lnd
            )
            response = self.client.SendPaymentSync(request)
            logger.warning(response)
        except Exception as e:
            logger.exception(e)

    def invoice_subscription(self, add_index):
        try:
            request = ln.InvoiceSubscription(
                add_index=add_index,
                # settle_index= 3,
            )
            for response in self.client.SubscribeInvoices(request):
                print(response)
                logger.warning(response)

        except Exception as e:
            logger.exception(e)

    def connect_peer(self, pubkey, host, permanent=False):
        return self.client.ConnectPeer(
            ln.ConnectPeerRequest(
                addr=ln.LightningAddress(pubkey=pubkey, host=host), perm=permanent
            )
        )

    def disconnect_from_peer(self, pubkey):
        return self.client.DisconnectPeer(
            ln.DisconnectPeerRequest(pub_key=pubkey)
        )

    def channel_balance(self):
        try:
            response = self.client.ChannelBalance(ln.ChannelBalanceRequest())
            return {
                'node': self.displayName,
                'balance': response.balance,
                'pending_open_balance': response.pending_open_balance
            }
        except Exception as e:
            logger.exception(e)

    def open_channel(self, **kwargs):
        # TODO check if channel already opened
        if not self.channel_exists_with_node(kwargs.get('node_pubkey_string')):
            try:
                request = ln.OpenChannelRequest(**kwargs)
                response = self.client.OpenChannelSync(request)
                return response
            except Exception as e:
                logger.exception(e)
        else:
            return []


def start():
    lnd_node = RpcClient(FAUCET_DOCKER)
    alice_node = RpcClient(ALICE_DOCKER)
    bob_node = RpcClient(BOB_DOCKER)

    logger.debug(alice_node.wallet_balance())
    logger.debug(bob_node.wallet_balance())

    # docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' lnd

    # Connect Alice to LND node
    if lnd_node.identity_pubkey not in alice_node.list_peers():
        alice_node.connect_peer(pubkey=lnd_node.getinfo().identity_pubkey, host='172.29.0.2')

    # Connect Bob to LND node
    if lnd_node.identity_pubkey not in bob_node.list_peers():
        bob_node.connect_peer(pubkey=lnd_node.getinfo().identity_pubkey, host='172.29.0.2')

    # Alice open channel to lnd

    # https://api.lightning.community/#openchannelsync

    print(list(alice_node.open_channel(
        node_pubkey=bytes.fromhex(lnd_node.identity_pubkey),
        node_pubkey_string=lnd_node.identity_pubkey,
        local_funding_amount=100000 + 9050,
        # The number of satoshis the wallet should commit to the channel
        push_sat=int(100000 / 2)
        # The number of satoshis to push to the remote side as part of the initial commitment state
    )))

    print(list(bob_node.open_channel(
        node_pubkey=bytes.fromhex(lnd_node.identity_pubkey),
        node_pubkey_string=lnd_node.identity_pubkey,
        local_funding_amount=100000 + 9050,
        # The number of satoshis the wallet should commit to the channel
        push_sat=int(100000 / 2)
        # The number of satoshis to push to the remote side as part of the initial commitment state
    )))

    logger.debug(f'{lnd_node} Active channels: {len([c.active for c in lnd_node.list_channels().channels])}')
    logger.debug(f'{alice_node} Active channels: {len([c.active for c in alice_node.list_channels().channels])}')
    logger.debug(f'{bob_node} Active channels: {len([c.active for c in bob_node.list_channels().channels])}')

    logger.debug(alice_node.channel_balance())
    logger.debug(bob_node.channel_balance())

    # IMPORTANT to send som value thought channels, every channel need balance > then amount you have to send

    logger.debug(bob_node.add_invoice(ammount=10, memo='Bob wants 10 satoshi from alice'))

    # logger.debug(node.invoice_subscription(3))

    if bob_node.list_invoices().invoices[len(bob_node.list_invoices().invoices) - 1]:
        payment_request = bob_node.list_invoices().invoices[len(bob_node.list_invoices().invoices) - 1].payment_request
        logger.info(payment_request)
        print('Alice -> send payment to bobs request')
        logger.debug(bob_node.decode_pay_request(payment_request))

        # Alice sends bob some btc
        logger.debug(alice_node.pay_invoice(payment_request))
