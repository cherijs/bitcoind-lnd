import logging
import time
from unittest import TestCase

from lnd import FAUCET_DOCKER, RpcClient, ALICE_DOCKER, BOB_DOCKER
from utils import get_docker_ip

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s', )
logger = logging.getLogger(__name__)


class TestRpcClient(TestCase):
    # def setUp(self):
    #     self.lnd_node = RpcClient(LND_DOCKER)
    #     self.alice_node = RpcClient(ALICE_DOCKER)
    #     self.bob_node = RpcClient(BOB_DOCKER)

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

    def test_connect_peer(self):

        alice_ip = get_docker_ip('alice')
        bob_ip = get_docker_ip('bob')

        peers = self.client('faucet').list_peers()
        if peers:
            logger.warning('Already connected, lets disconnect')
            for peer in peers:
                # logger.debug(f'Disconnecting: {peer}')
                self.client('faucet').disconnect_from_peer(peer)
            self.assertEqual([], self.client('faucet').list_peers())

        time.sleep(1)
        logger.info('Lets connect.. to alice an bob')

        # $ docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' alice
        alice_pubkey = self.client('alice').identity_pubkey
        self.client('faucet').connect_peer(pubkey=alice_pubkey,
                                           host=alice_ip)

        # $ docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' bob
        bob_pubkey = self.client('bob').identity_pubkey
        self.client('faucet').connect_peer(pubkey=bob_pubkey,
                                           host=bob_ip)

        time.sleep(1)
        self.assertEqual(2, len(self.client('faucet').list_peers()))

        # logger.debug(self.client('faucet').getnode_info(alice_pubkey))

    # def test_list_peers(self):
    #     print(self.client('faucet').list_peers())

    # def test_getinfo(self):
    #     self.fail()
    #
    # def test_wallet_balance(self):
    #     self.fail()
    #
    # def test_invoice_subscription(self):
    #     self.fail()
    #
    # def test_list_channels(self):
    #     self.fail()
    #
    # def test_list_pending_channels(self):
    #     self.fail()
    #
    # def test_channel_exists_with_node(self):
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
    #
    #
    # def test_channel_balance(self):
    #     self.fail()
    #
    # def test_open_channel(self):
    #     self.fail()
