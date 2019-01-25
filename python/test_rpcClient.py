import logging
import time
import warnings
from unittest import TestCase

from bitcoinrpc.authproxy import AuthServiceProxy

from lnd import FAUCET_DOCKER, RpcClient, ALICE_DOCKER, BOB_DOCKER
from utils import get_docker_ip

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s', )
logger = logging.getLogger(__name__)


# logging.getLogger("BitcoinRPC").setLevel(logging.WARNING)


def ignore_warnings(test_func):
    def do_test(self, *args, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            test_func(self, *args, **kwargs)

    return do_test


class TestRpcClient(TestCase):
    @ignore_warnings
    def setUp(self):
        self.alice_ip = get_docker_ip('alice')
        self.bob_ip = get_docker_ip('bob')
        self.faucet_ip = get_docker_ip('lnd')
        # self.lnd_node = RpcClient(LND_DOCKER)
        # self.alice_node = RpcClient(ALICE_DOCKER)
        # self.bob_node = RpcClient(BOB_DOCKER)
        # rpc_user and rpc_password are set in the bitcoin.conf file
        rpc_user = 'test'
        rpc_password = 'test'
        port = 18443
        self.rpc_host = "http://%s:%s@127.0.0.1:%s" % (rpc_user, rpc_password, port)

    def client(self, node):
        """

        :rtype: RpcClient
        """
        try:
            current_node = getattr(self, node)
        except AttributeError as e:

            if node == 'alice':
                conf = ALICE_DOCKER
            elif node == 'bob':
                conf = BOB_DOCKER
            else:
                conf = FAUCET_DOCKER

            setattr(self, node, RpcClient(conf))
            current_node = getattr(self, node)

        return current_node

    @ignore_warnings
    def test_btc(self):
        rpc_connection = AuthServiceProxy(self.rpc_host)
        get_wallet_info = rpc_connection.getwalletinfo()
        self.assertIsNotNone(get_wallet_info)

    def test_ping(self):
        self.assertIs(True, self.client('faucet').ping())

    def test_disconnect_peer(self):
        peers = self.client('faucet').list_peers()
        if peers:
            logger.warning('Already connected, lets disconnect')
            for peer in peers:
                logger.debug(f'Disconnecting: {peer}')
                self.client('faucet').disconnect_from_peer(peer)
            self.assertEqual([], self.client('faucet').list_peers())
        else:
            try:
                self.connect_to_peer('faucet', 'alice')
                self.test_disconnect_peer()
            except Exception as e:
                self.fail(e)
        time.sleep(1)

    def test_connect_peer(self):
        try:
            self.connect_to_peer('faucet', 'alice')
        except Exception as e:
            self.fail(e)

        try:
            self.connect_to_peer('faucet', 'bob')
        except Exception as e:
            self.fail(e)

    def connect_to_peer(self, who, to):
        logger.info('Lets connect.. to ' + to)
        to_pubkey = self.client(to).identity_pubkey

        # TODO make async get_docker_ip
        tip = f'{to}_ip'
        ip = getattr(self, tip)

        assert ip, f'Can\'t get {to} ip'

        return self.client(who).connect_peer(pubkey=to_pubkey, host=ip)

    def test_list_peers(self):
        try:
            self.connect_to_peer('faucet', 'alice')
        except Exception as e:
            self.fail(e)

        try:
            peers = self.client('faucet').list_peers()
            self.assertGreater(len(peers), 0)
        except Exception as e:
            self.fail(e)

    def test_getinfo(self):
        try:
            self.connect_to_peer('faucet', 'alice')
        except Exception as e:
            self.fail(e)

        try:
            info = self.client('faucet').getinfo()
            self.assertTrue(info)
        except Exception as e:
            self.fail(e)

    def test_wallet_balance(self):
        try:
            self.connect_to_peer('faucet', 'alice')
        except Exception as e:
            self.fail(e)

        try:
            balance = self.client('faucet').wallet_balance()
            self.assertTrue(balance.get('total_balance'))
        except Exception as e:
            self.fail(e)

    def test_channel_exists_with_node(self):
        try:
            self.connect_to_peer('faucet', 'alice')
        except Exception as e:
            self.fail(e)

        try:
            channel = self.client('faucet').channel_exists_with_node(self.client('alice').identity_pubkey)
            self.assertIsNotNone(channel)
        except Exception as e:
            self.fail(e)

    def test_list_channels(self):
        try:
            channels = self.client('faucet').list_channels()
            self.assertIsNotNone(channels.channels)
        except Exception as e:
            self.fail(e)

    def test_list_pending_channels(self):
        try:
            channels = self.client('faucet').list_pending_channels()
            self.assertIsNotNone(channels.pending_open_channels)
        except Exception as e:
            self.fail(e)

    def test_channel_balance(self):
        try:
            balance = self.client('faucet').channel_balance()
            # logger.debug(balance)
            self.assertIsNotNone(balance.get('balance'))
        except Exception as e:
            self.fail(e)

    @ignore_warnings
    def test_open_channel(self):
        try:
            self.connect_to_peer('faucet', 'alice')
        except Exception as e:
            self.fail(e)

        try:
            channel_point = self.client('alice').open_channel(
                node_pubkey=bytes.fromhex(self.client('faucet').identity_pubkey),
                node_pubkey_string=self.client('faucet').identity_pubkey,
                local_funding_amount=100000 + 9050,
                push_sat=int(100000 / 2))

            # {
            #     "funding_txid_bytes": <bytes>,
            #     "funding_txid_str": <string>,
            #     "output_index": <uint32>,
            # }

            logger.debug(channel_point)
            self.assertIsNotNone(channel_point)
        except Exception as e:
            self.assertEqual('Channel already opened', e.args[0])

        # GENERATE 10 blocks, to confirm channel
        rpc_connection = AuthServiceProxy(self.rpc_host)
        blocks = rpc_connection.generate(10)
        self.assertGreaterEqual(len(blocks), 10)

        try:
            channels = self.client('alice').list_channels()
            self.assertIsNotNone(channels.channels)
            self.assertTrue(self.client('faucet').identity_pubkey in set(ch.remote_pubkey for ch in channels.channels))
        except Exception as e:
            self.fail(e)

    # def test_invoice_subscription(self):
    #     self.fail()
    #
    # def test_add_invoice(self):
    #     self.fail()
    #
    # def test_list_invoices(self):
    #     self.fail()
    #
    # def test_decode_pay_request(self):
    #     self.fail()
    #
    # def test_send_payment(self):
    #     self.fail()
    #
    # def test_pay_invoice(self):
    #     self.fail()
