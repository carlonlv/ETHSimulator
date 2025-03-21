from typing import Union

from eth_account import Account
from eth_account.signers.local import LocalAccount
from pydantic import BaseModel, Field, field_validator
from web3 import Web3

from ethsimulator.service_manager import ServiceManager


class TransactionManager(BaseModel):
    """
    Manages Ethereum transactions between accounts using Web3.py.

    :param web3: Web3 - An instance of Web3 connected to an Ethereum node.
    """

    service_manager: ServiceManager = Field(..., description="ServiceManager instance for connecting to the Ethereum node.")

    @property
    def web3(self) -> Web3:
        """Returns the Web3 instance from the ServiceManager."""
        return self.service_manager.get_web3()

    @field_validator("service_manager")
    def _check_web3_connection(cls, v: ServiceManager) -> ServiceManager:
        """Validates the Web3 connection.

        :param v: ServiceManager - The ServiceManager instance.
        :type v: ServiceManager
        :return: The validated ServiceManager instance.
        :rtype: ServiceManager
        """
        v.check_clients()
        if not v.is_client_running():
            v.connect()
        return v

    def send_transaction(self, sender: Union[LocalAccount, str], private_key: str, recipient: str, amount_ether: float) -> str:
        """
        Executes a transaction from the sender to the recipient with the specified amount of Ether.

        :param sender: Union[LocalAccount, str] - The sender's account (LocalAccount object or address string).
        :param private_key: str - The private key of the sender's account.
        :param recipient: str - The recipient's Ethereum address.
        :param amount_ether: float - The amount of Ether to send.
        :return: str - The transaction hash.
        """
        # Validate recipient address
        if not self.web3.is_address(recipient):
            raise ValueError(f"Invalid recipient address: {recipient}")

        # Convert Ether amount to Wei
        amount_wei = self.web3.to_wei(amount_ether, "ether")

        # Get the nonce (transaction count) for the sender
        sender_address = sender.address if isinstance(sender, LocalAccount) else self.web3.to_checksum_address(sender)
        nonce = self.web3.eth.get_transaction_count(sender_address)

        # Build the transaction dictionary
        tx = {
            "nonce": nonce,
            "to": recipient,
            "value": amount_wei,
            "gas": 21000,  # Standard gas limit for Ether transfer
            "gasPrice": self.web3.eth.gas_price,  # Current gas price
        }

        # Sign the transaction
        signed_tx = self.web3.eth.account.sign_transaction(tx, private_key)

        # Send the signed transaction
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)

        return tx_hash.hex()


if __name__ == "__main__":
    # Connect to the Ethereum node
    w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

    # Ensure connection is successful
    if not w3.is_connected():
        raise ConnectionError("Failed to connect to the Ethereum node.")

    # Sender's address and private key
    sender_address = "0xYourSenderAddress"
    sender_private_key = "0xYourSenderPrivateKey"

    # Create a LocalAccount object for the sender
    sender_account = Account.from_key(sender_private_key)

    # Recipient's address
    recipient_address = "0xRecipientAddress"

    # Amount to send (in Ether)
    amount = 0.01

    service_manager = ServiceManager(
        client_type="reth",  # Change to "geth" for Geth
        datadir="./reth_data",
        extra_args={"--network": "mainnet"},  # Example extra argument
    )
    service_manager.initialize_blockchain()
    service_manager.connect()

    tx_manager = TransactionManager(
        service_manager=service_manager
    )

    # Execute the transaction
    try:
        tx_hash = tx_manager.send_transaction(sender_account, sender_private_key, recipient_address, amount)
        print(f"Transaction successful with hash: {tx_hash}")
    except Exception as e:
        print(f"An error occurred: {e}")
