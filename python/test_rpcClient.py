import logging
import time
from unittest import TestCase

from lnd import FAUCET_DOCKER, RpcClient, ALICE_DOCKER, BOB_DOCKER
from utils import get_docker_ip

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s', )
logger = logging.getLogger(__name__)


class TestRpcClient(TestCase):
    def setUp(self):
        self.alice_ip = get_docker_ip('alice')
        self.bob_ip = get_docker_ip('bob')
        self.faucet_ip = get_docker_ip('faucet')
        # self.lnd_node = RpcClient(LND_DOCKER)
        # self.alice_node = RpcClient(ALICE_DOCKER)
        # self.bob_node = RpcClient(BOB_DOCKER)

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

    # def test_invoice_subscription(self):
    #     self.fail()
    #
    # def test_list_channels(self):
    #     self.fail()
    #
    # def test_list_pending_channels(self):
    #     self.fail()
    #
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
    #
    #
    # def test_channel_balance(self):
    #     self.fail()
    #
    # def test_open_channel(self):
    #     self.fail()
