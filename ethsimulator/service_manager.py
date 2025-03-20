import subprocess
import time
from typing import Dict, Literal, Optional

import psutil
from pydantic import BaseModel, Field
from web3 import Web3


class ServerManager(BaseModel):
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

    def connect(self) -> Web3:
        """
        Connects to the execution client. If the client is not running, it starts a new instance.

        :return: Web3 - A Web3 instance connected to the client.
        """
        if not self._is_client_running():
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

    def _is_client_running(self) -> bool:
        """
        Checks if the Reth or Geth process is already running.

        :return: bool - True if the process is running, False otherwise.
        """
        process_name = "reth" if self.client_type == "reth" else "geth"
        for proc in psutil.process_iter(attrs=["pid", "name"]):
            if process_name in proc.info["name"]:
                return True
        return False

    def _is_rpc_active(self) -> bool:
        """
        Checks if the RPC endpoint is responding.

        :return: bool - True if RPC is active, False otherwise.
        """
        try:
            temp_web3 = Web3(Web3.HTTPProvider(self.rpc_url))
            return temp_web3.is_connected()
        except Exception:
            return False

    def _start_client(self) -> None:
        """
        Starts the execution client (Reth/Geth) as a background process with user-defined arguments.

        :return: None
        """
        if self.client_type == "reth":
            command = ["reth", "node", "--http", "--http.addr", "0.0.0.0", "--http.port", "8545", "--datadir", self.datadir]
        elif self.client_type == "geth":
            command = ["geth", "--http", "--http.addr", "0.0.0.0", "--http.port", "8545", "--datadir", self.datadir, "--syncmode", "full"]
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
    server = ServerManager(
        client_type="reth",  # Change to "geth" for Geth
        datadir="./reth_data",
        extra_args={"--network": "mainnet"},  # Example extra argument
    )

    web3_instance = server.connect()
    print(f"🔗 Web3 Connected: {web3_instance.is_connected()}")
