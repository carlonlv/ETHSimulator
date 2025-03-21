import json
import os
import subprocess
import time
from typing import Dict, Literal, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field
from web3 import Web3


class ServiceManager(BaseModel):
    """
    Manages connection to a Reth or Geth execution client.
    If the client is not running, it starts a new process with specified arguments.

    :param client_type: Literal["reth", "geth"] - The execution client to connect/start.
    :param rpc_url: str - The RPC endpoint for Web3 connection.
    :param datadir: str - Path to the blockchain data directory.
    :param extra_args: Dict[str, str] - Additional CLI arguments for starting the client.
    """

    client_type: Literal["reth", "geth"] = Field(..., description="Execution client type: Reth or Geth.")
    rpc_url: str = Field("http://127.0.0.1:8545", description="RPC URL for Web3 connection.")
    datadir: str = Field(..., description="Path to blockchain data directory.")
    extra_args: Dict[str, str] = Field(default={}, description="Additional arguments for client startup.")

    _web3: Optional[Web3] = None
    _process: Optional[subprocess.Popen] = None

    def check_clients(self) -> None:
        """Checks if Geth and Reth are installed and prints their versions."""
        clients = {"geth": ["geth", "version"], "reth": ["reth", "--version"]}

        client = self.client_type
        command = clients[client]
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            version_info = result.stdout.strip()
            print(f"{client.capitalize()} is installed. Version info:\n{version_info}\n")
        except FileNotFoundError:
            raise FileNotFoundError(f"{client.capitalize()} is not installed or not found in the system PATH.\n")
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while checking {client.capitalize()}: {e}\n")

    def connect(self) -> Web3:
        """
        Connects to the execution client. If the client is not running, it starts a new instance.

        :return: A Web3 instance connected to the client.
        :rtype: Web3
        """
        if not self.is_client_running():
            print(f"⚠️ {self.client_type.upper()} client not running. Starting it now...")
            self._start_client()

        # Wait for client to become responsive
        for _ in range(10):
            if self._is_rpc_active():
                print(f"✅ Connected to {self.client_type.upper()} at {self.rpc_url}")
                self._web3 = Web3(Web3.HTTPProvider(self.rpc_url))
                return self._web3
            time.sleep(1)

        raise ConnectionError(f"❌ Failed to connect to {self.client_type.upper()} at {self.rpc_url}")

    def initialize_blockchain(self, genesis_path: Optional[str] = None, players_path: Optional[str] = None) -> None:
        """
        Initializes the blockchain with a custom genesis.json file and player balances.

        :param genesis_path: Path to a custom genesis.json file.
        :type genesis_path: str
        :param players_path: Path to a players.json file with player addresses and balances.
        :type players_path: str
        """

        # Check if the blockchain is already initialized
        if os.path.exists(os.path.join(self.datadir, "geth")) or os.path.exists(os.path.join(self.datadir, "reth")):
            print("Blockchain already initialized.")
            return

        # Load or create genesis.json
        if genesis_path and os.path.isfile(genesis_path):
            with open(genesis_path, "r") as file:
                genesis_data = json.load(file)
        else:
            genesis_data = {"config": {"chainId": 1337, "homesteadBlock": 0, "eip150Block": 0, "eip155Block": 0, "eip158Block": 0}, "difficulty": "0x400", "gasLimit": "0x8000000", "alloc": {}}

        # Incorporate players.json if provided
        if players_path and os.path.isfile(players_path):
            with open(players_path, "r") as file:
                players_data = json.load(file)
            for player in players_data:
                address = player["address"]
                balance = player.get("balance", "1000000000000000000")  # Default 1 ETH
                genesis_data["alloc"][address] = {"balance": balance}

        # Save the modified genesis.json
        modified_genesis_path = os.path.join(self.datadir, "genesis.json")
        with open(modified_genesis_path, "w") as file:
            json.dump(genesis_data, file, indent=4)

        # Initialize the blockchain
        if self.client_type == "geth":
            subprocess.run(["geth", "--datadir", self.datadir, "init", modified_genesis_path])
        elif self.client_type == "reth":
            subprocess.run(["reth", "init", "--datadir", self.datadir, "--chain", modified_genesis_path])
        else:
            raise ValueError("Unsupported client type. Use 'geth' or 'reth'.")

    def is_client_running(self) -> bool:
        """
        Checks if the Reth or Geth process is already running.

        :return: True if the process is running, False otherwise.
        :rtype: bool
        """
        return self._web3 is not None and self._web3.is_connected()

    def _is_rpc_active(self) -> bool:
        """
        Checks if the RPC endpoint is responding.

        :return: True if RPC is active, False otherwise.
        :rtype: bool
        """
        try:
            temp_web3 = Web3(Web3.HTTPProvider(self.rpc_url))
            return temp_web3.is_connected()
        except Exception:
            return False

    def _start_client(self) -> None:
        """Starts the execution client (Reth/Geth) as a background process with user-defined arguments."""

        parsed_url = urlparse(self.rpc_url)
        host = parsed_url.hostname or "127.0.0.1"
        port = str(parsed_url.port or 8545)

        if self.client_type == "reth":
            command = ["reth", "node", "--http", "--http.addr", host, "--http.port", port, "--datadir", self.datadir]
        elif self.client_type == "geth":
            command = ["geth", "--http", "--http.addr", host, "--http.port", port, "--datadir", self.datadir, "--syncmode", "full"]
        else:
            raise ValueError("Invalid client type. Choose 'reth' or 'geth'.")

        # Append extra arguments provided by the user
        for key, value in self.extra_args.items():
            command.append(key)
            if value:
                command.append(str(value))

        # Start the process
        self._process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"🚀 Started {self.client_type.upper()} with PID {self._process.pid}")

    def stop_client(self) -> None:
        """
        Stops the execution client process if it was started by this instance.

        :return: None
        """
        if self._process:
            self._process.terminate()
            self._process.wait()
            print(f"🛑 Stopped {self.client_type.upper()} process.")
            self._process = None

    def get_web3(self) -> Web3:
        """
        Returns the connected Web3 instance.

        :return: Web3 - A connected Web3 instance.
        """
        if self._web3 is None:
            raise ValueError("Web3 instance is not initialized. Call `connect()` first.")
        return self._web3


if __name__ == "__main__":
    # Example: Connect to Reth and start it if needed
    server = ServiceManager(
        client_type="reth",  # Change to "geth" for Geth
        datadir="./reth_data",
        extra_args={"--network": "mainnet"},  # Example extra argument
    )

    # Check if Reth is installed
    server.check_clients()

    # Init a new blockchain with custom genesis and player balances
    server.initialize_blockchain(genesis_path="../genesis.json", players_path="players.json")

    web3_instance = server.connect()
    print(f"🔗 Web3 Connected: {web3_instance.is_connected()}")
