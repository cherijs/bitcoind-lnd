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
    'wallet': '/Users/cherijs/.docker_volumes/.lnd/data/chain/bitcoin/regtest/wallet.db',
    'logs': '/Users/cherijs/.docker_volumes/.lnd/logs/',
    'admin_macaroon': '/Users/cherijs/.docker_volumes/.lnd/data/chain/bitcoin/regtest/admin.macaroon'
}

ALICE_DOCKER = {
    'name': 'Alice',
    'node_host': 'localhost:9010',
    'rpc_host': 'localhost:10010',
    'tls_cert': '/Users/cherijs/.docker_volumes/simnet/alice/tls.cert',
    'wallet': '/Users/cherijs/.docker_volumes/simnet/alice/data/chain/bitcoin/regtest/wallet.db',
    'logs': '/Users/cherijs/.docker_volumes/simnet/alice/logs/',
    'admin_macaroon': '/Users/cherijs/.docker_volumes/simnet/alice/data/chain/bitcoin/regtest/admin.macaroon'
}

BOB_DOCKER = {
    'name': 'Bob',
    'node_host': 'localhost:9011',
    'rpc_host': 'localhost:10011',
    'tls_cert': '/Users/cherijs/.docker_volumes/simnet/bob/tls.cert',
    'wallet': '/Users/cherijs/.docker_volumes/simnet/bob/data/chain/bitcoin/regtest/wallet.db',
    'logs': '/Users/cherijs/.docker_volumes/simnet/bob/logs/',
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

    def address(self):
        try:
            response = self.client.NewAddress(ln.NewAddressRequest())
            return response
        except Exception as e:
            logger.exception(e)

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

        assert host, "Host is empty."
        assert pubkey, "Pubkey is empty."

        try:
            addr = ln.LightningAddress(pubkey=pubkey, host=host)
        except Exception as e:
            raise AssertionError(f'Cant create LightningAddress from host:{host} ->  pubkey:{pubkey}')

        try:
            request = ln.ConnectPeerRequest(addr=addr, perm=permanent)
        except Exception as e:
            raise AssertionError('Cant create peer request')

        try:
            response = self.client.ConnectPeer(request)
            return response
        except Exception as e:
            if str(e.details()).startswith('already connected to peer'):
                pass
            else:
                raise AssertionError(f'Can\'t connect to {host}! {e.details()}')

        return

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

    def close_peer_channels(self, peer, force):
        connected_channel_list = list(self.list_channels().channels)
        connected_channel_points = set(ch.channel_point for ch in connected_channel_list if ch.remote_pubkey == peer)
        if connected_channel_points:
            for channel_point in connected_channel_points:
                # The outpoint (txid:index) of the funding transaction. With this value, Bob will be able to generate a signature for Alice’s version of the commitment transaction.
                cp = ln.ChannelPoint(funding_txid_bytes=bytes(channel_point.split(':')[0], 'utf-8'),
                                     funding_txid_str=u'{}'.format(channel_point.split(':')[0]),
                                     output_index=int(channel_point.split(':')[1])
                                     )
                logger.debug(self.close_channel(channel_point=cp, force=force))

    def close_channel(self, channel_point, force):
        try:

            request = ln.CloseChannelRequest(
                channel_point=channel_point,
                force=force,
                target_conf=1,
                # sat_per_byte=<int64>
            )
            response = self.client.CloseChannel(request)
            return response
        except Exception as e:
            logger.exception(e)

    def open_channel(self, **kwargs):
        if not self.channel_exists_with_node(kwargs.get('node_pubkey_string')) or kwargs.get('force'):
            try:
                if kwargs.get('force') is not None:
                    del kwargs['force']
                request = ln.OpenChannelRequest(**kwargs)
                response = self.client.OpenChannelSync(request)
                return response
            except Exception as e:
                logger.exception(e)
        else:
            raise AssertionError('Channel already opened')

    def stop(self):
        try:
            response = self.client.StopDaemon(ln.StopRequest())
            return response
        except Exception as e:
            logger.exception(e)
