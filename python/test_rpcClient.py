import logging
import os
import shutil
import time
import warnings
from unittest import TestCase

from bitcoinrpc.authproxy import AuthServiceProxy

from lnd import FAUCET_DOCKER, RpcClient, ALICE_DOCKER, BOB_DOCKER
from utils import get_docker_ip, restart_docker

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
    cleaned = False

    @classmethod
    def setUpClass(cls):
        """ get_some_resource() is slow, to avoid calling it for each test use setUpClass()
            and store the result as class variable
        """

        def clean_wallets():

            # REMOVE wallets, to start clean
            logger.error('-------  CLEAN WALLETS  -------')
            # if os.path.isdir(ALICE_DOCKER['wallet']):
            #     shutil.rmtree(ALICE_DOCKER['wallet'])
            # if os.path.isdir(BOB_DOCKER['wallet']):
            #     shutil.rmtree(BOB_DOCKER['wallet'])
            # if os.path.isdir(FAUCET_DOCKER['wallet']):
            #     shutil.rmtree(FAUCET_DOCKER['wallet'])

            if os.path.exists(ALICE_DOCKER['wallet']):
                os.remove(ALICE_DOCKER['wallet'])
            if os.path.exists(BOB_DOCKER['wallet']):
                os.remove(BOB_DOCKER['wallet'])
            if os.path.exists(FAUCET_DOCKER['wallet']):
                os.remove(FAUCET_DOCKER['wallet'])

            if os.path.isdir(ALICE_DOCKER['logs']):
                shutil.rmtree(ALICE_DOCKER['logs'])
            if os.path.isdir(BOB_DOCKER['logs']):
                shutil.rmtree(BOB_DOCKER['logs'])
            if os.path.isdir(FAUCET_DOCKER['logs']):
                shutil.rmtree(FAUCET_DOCKER['logs'])
            restart_docker('lnd')
            restart_docker('alice')
            restart_docker('bob')
            # wait for containers initialise
            time.sleep(15)

        super(TestRpcClient, cls).setUpClass()
        # clean_wallets()
        cls.alice_ip = get_docker_ip('alice')
        cls.bob_ip = get_docker_ip('bob')
        cls.faucet_ip = get_docker_ip('lnd')
        # rpc_user and rpc_password are set in the bitcoin.conf file
        rpc_user = 'test'
        rpc_password = 'test'
        port = 18443
        cls.rpc_host = "http://%s:%s@127.0.0.1:%s" % (rpc_user, rpc_password, port)

    @ignore_warnings
    def setUp(self):
        alice_synced = False
        bob_synced = False
        lnd_synced = False
        while True:
            if not alice_synced:
                alice_synced = self.synced_to_chain('alice')

            if not bob_synced:
                bob_synced = self.synced_to_chain('bob')

            if not lnd_synced:
                lnd_synced = self.synced_to_chain('lnd')

            if alice_synced and bob_synced and lnd_synced:
                break
            logger.error('LND not synced to chain! Generate more blocks?')
            rpc_connection = AuthServiceProxy(self.rpc_host)
            blocks = rpc_connection.generate(1)
            time.sleep(5)

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

    def synced_to_chain(self, node):
        try:
            info = self.client(node).getinfo()
            return info.synced_to_chain
        except Exception as e:
            self.fail(e)

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
            info = self.client('faucet').getinfo()
            self.assertTrue(info)
        except Exception as e:
            self.fail(e)

    def test_wallet_balance(self):
        try:
            balance = self.client('faucet').wallet_balance()
            logger.debug(balance.get('total_balance'))
            self.assertIsNotNone(balance.get('total_balance'))
        except Exception as e:
            self.fail(e)

    def test_channel_exists_with_node(self):
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
            logger.debug(balance)
            self.assertIsNotNone(balance.get('balance'))
        except Exception as e:
            self.fail(e)

    @ignore_warnings
    def send_btc_to_node(self, node, amount=100000000):
        try:
            balance = self.client(node).wallet_balance()
            logger.info(balance)
            if not balance.get('confirmed_balance') or balance.get('confirmed_balance') < amount:
                faucet_address = self.client(node).address().address
                #     send bitcoin to faucet_address
                rpc_connection = AuthServiceProxy(self.rpc_host)
                tx = rpc_connection.sendtoaddress(faucet_address,
                                                  amount / 100000000 - balance.get('confirmed_balance') / 100000000)
                blocks = rpc_connection.generate(3)
                self.send_btc_to_node(node)
        except Exception as e:
            self.fail(e)

    @ignore_warnings
    def test_open_channel(self):
        try:
            self.connect_to_peer('faucet', 'alice')
            self.connect_to_peer('faucet', 'bob')
        except Exception as e:
            self.fail(e)

        self.send_btc_to_node('alice', amount=100000000)
        self.send_btc_to_node('bob', amount=100000000)

        # alice and bob opens one wau funded channels with faucet
        try:
            commit_fee = 9050
            channel_point = self.client('alice').open_channel(
                node_pubkey=bytes.fromhex(self.client('faucet').identity_pubkey),
                node_pubkey_string=self.client('faucet').identity_pubkey,
                local_funding_amount=int(0.1 * 100000000),
                push_sat=0)
            self.assertIsNotNone(channel_point)


        except Exception as e:
            self.assertEqual('Channel already opened', e.args[0])
        try:
            commit_fee = 9050
            channel_point = self.client('bob').open_channel(
                node_pubkey=bytes.fromhex(self.client('faucet').identity_pubkey),
                node_pubkey_string=self.client('faucet').identity_pubkey,
                local_funding_amount=int(0.1 * 100000000),
                push_sat=0)
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
