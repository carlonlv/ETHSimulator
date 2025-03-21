from typing import Any, Dict, List, Literal, Tuple, Union

import numpy as np
from pydantic import BaseModel, Field, PositiveInt, PrivateAttr

from ethsimulator.account_creation import AccountCreator, BalanceSamplerConfig
from ethsimulator.service_manager import ServiceManager
from ethsimulator.transaction_manager import TransactionManager


class TransactionPlayerSamplerConfig(BaseModel):
    """
    Configuration for sampling Ethereum player addresses and private keys.
    """

    distribution: Literal["random", "zipf"] = Field("random", description="Method for sampling from and to player addresses.")
    zipf_alpha: float = Field(1.0, ge=1, description="Zipf distribution parameter 'a' (default: 1.0).")


class TransactionAmountSamplerConfig(BaseModel):
    """
    Configuration for sampling transaction amounts in Ether.
    """

    distribution: Literal["uniform", "normal"] = Field("uniform", description="Method for sampling transaction amounts.")
    amount_min: float = Field(0.01, description="Minimum transaction amount in Ether.")
    amount_max: float = Field(100, description="Maximum transaction amount in Ether.")
    normal_mean: float = Field(1.0, description="Mean transaction amount in Ether.")
    normal_std: float = Field(0.1, description="Standard deviation of transaction amount in Ether.")


class TransactionInterarrivalSamplerConfig(BaseModel):
    """
    Configuration for sampling transaction arrival times.
    """
    distribution: Literal["exponential", "constant"] = Field("exponential", description="Method for sampling transaction interarrival times.")
    period: float = Field(1.0, description="Average time between transactions in seconds.")


class TransactionSimulator(BaseModel):
    """
    Simulates Ethereum transactions between multiple players using a Poisson arrival process.

    :param transaction_manager: TransactionManager instance connected to the Ethereum network.
    :param players: List of player dictionaries containing 'address' and 'private_key'.
    :param rate: Average number of transactions per unit time (λ) for the Poisson process.
    :param distribution: Distribution type for selecting sender and recipient pairs ('uniform' or 'zipf').
    :param amount_min: Minimum transaction amount in Ether.
    :param amount_max: Maximum transaction amount in Ether.
    :param zipf_param: Parameter 'a' for the Zipfian distribution (must be > 1).
    """

    ## Initialization
    num_accounts: PositiveInt = Field(..., description="Number of Ethereum accounts to generate.")
    balance_sampler_config: BalanceSamplerConfig = Field(..., description="Configuration for balance sampling.")
    chain_id: PositiveInt = Field(1337, description="Ethereum chain ID.")
    output_dir: str = Field(".", description="Directory to save generated files.")

    # Chain settings
    client_type: Literal["reth", "geth"] = Field(..., description="Execution client type: Reth or Geth.")
    rpc_url: str = Field("http://127.0.0.1:8545", description="RPC URL for Web3 connection.")
    datadir: str = Field(..., description="Path to blockchain data directory.")
    extra_args: Dict[str, str] = Field(default={}, description="Additional arguments for client startup.")

    # Environment settings
    transaction_player_sampler_config: TransactionPlayerSamplerConfig = Field(..., description="Configuration for sampling player addresses.")
    transaction_amount_sampler_config: TransactionAmountSamplerConfig = Field(..., description="Configuration for sampling transaction amounts.")
    transaction_interarrival_sampler_config: TransactionInterarrivalSamplerConfig = Field(..., description="Configuration for sampling transaction interarrival times.")

    _players: List[Tuple[str, str]] = PrivateAttr()
    _transaction_manager: TransactionManager = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        # Initialize the TransactionManager
        service_manager = ServiceManager(
            client_type=self.client_type,
            rpc_url=self.rpc_url,
            datadir=self.datadir,
            extra_args=self.extra_args,
        )
        service_manager.initialize_blockchain()
        service_manager.connect()

        self._transaction_manager = TransactionManager(
            service_manager=service_manager
        )
        # Generate Ethereum accounts for players
        account_creator = AccountCreator(
            num_accounts=self.num_accounts,
            balance_sampler_config=self.balance_sampler_config,
            chain_id=self.chain_id,
            output_dir=self.output_dir,
        )
        account_creator.generate_accounts()
        self._players = [(acc["address"], acc["private_key"]) for acc in account_creator.get_accounts()]

    # def __init__(self, transaction_manager: TransactionManager, players: List[Dict[str, str]], rate: float, distribution: str = "uniform", amount_min: float = 0.01, amount_max: float = 1.0, zipf_param: float = 2.0):
    #     self.transaction_manager = transaction_manager
    #     self.players = players
    #     self.rate = rate
    #     self.distribution = distribution
    #     self.amount_min = amount_min
    #     self.amount_max = amount_max
    #     self.zipf_param = zipf_param
    #     self.num_accounts = len(players)

    #     # Validate distribution choice
    #     if self.distribution not in ["uniform", "zipf"]:
    #         raise ValueError("Distribution must be either 'uniform' or 'zipf'.")

    #     # Validate Zipf parameter
    #     if self.distribution == "zipf" and self.zipf_param <= 1:
    #         raise ValueError("Zipf parameter 'a' must be greater than 1.")

    #     # Precompute Zipf probabilities if needed
    #     if self.distribution == "zipf":
    #         ranks = np.arange(1, self.num_accounts + 1)
    #         self.zipf_probs = 1 / np.power(ranks, self.zipf_param)
    #         self.zipf_probs /= self.zipf_probs.sum()

    def _select_players(self) -> Tuple[Tuple[str, str], Tuple[str, str]]:
        """
        Selects sender and recipient players based on the specified distribution.

        :return: Tuple containing sender and recipient player tuples.
        :rtype: Tuple[Dict[str, str], Dict[str, str]]
        """
        match self.transaction_player_sampler_config.distribution:
            case "uniform":
                sender_idx, recipient_idx = np.random.choice(self.num_accounts, 2, replace=False)
            case "zipf":
                ranks = np.arange(1, self.num_accounts + 1)
                self.zipf_probs = 1 / np.power(ranks, self.transaction_player_sampler_config.zipf_alpha)
                self.zipf_probs /= self.zipf_probs.sum()
                sender_idx, recipient_idx = np.random.choice(self.num_accounts, 2, replace=False, p=self.zipf_probs)
        sender = self._players[sender_idx]
        recipient = self._players[recipient_idx]
        return sender, recipient

    def _generate_transaction_amount(self) -> float:
        """
        Generates a transaction amount sampled from a Uniform distribution.

        :return: Transaction amount in Ether.
        """
        match self.transaction_amount_sampler_config.distribution:
            case "uniform":
                return np.random.uniform(self.transaction_amount_sampler_config.amount_min, self.transaction_amount_sampler_config.amount_max)
            case "normal":
                result = np.random.normal(loc=self.transaction_amount_sampler_config.amount_min, scale=self.transaction_amount_sampler_config.amount_max)
                if result < self.transaction_amount_sampler_config.amount_min:
                    return self.transaction_amount_sampler_config.amount_min
                if result > self.transaction_amount_sampler_config.amount_max:
                    return self.transaction_amount_sampler_config.amount_max
                return result

    def _generate_interarrival_time(self) -> float:
        """
        Generates a random interarrival time between transactions.

        :return: Interarrival time in seconds.
        """
        match self.transaction_interarrival_sampler_config.distribution:
            case "exponential":
                return np.random.exponential(self.transaction_interarrival_sampler_config.period)
            case "constant":
                return self.transaction_interarrival_sampler_config.period

    def _simulate_transaction(self) -> None:
        """
        Simulates a single transaction between two players.
        """
        sender, recipient = self._select_players()
        amount = self._generate_transaction_amount()

        try:
            tx_hash = self._transaction_manager.send_transaction(sender=sender[0], private_key=sender[1], recipient=recipient[0], amount_ether=amount)
            print(f"Transaction successful: {sender[0]} -> {recipient[0]} | Amount: {amount} ETH | TxHash: {tx_hash}")
        except Exception as e:
            print(f"Transaction failed: {e}")

    def run_simulation(self, duration: Union[float, None] = None, num_transactions: Union[int, None] = None):
        """
        Runs the transaction simulation.

        :param duration: Total simulation time in seconds. If None, num_transactions must be specified.
        :param num_transactions: Total number of transactions to simulate. If None, duration must be specified.
        """
        assert (duration is not None) + (num_transactions is not None) == 1, "Either duration or num_transactions must be specified."

        if duration is not None:
            # Simulate based on duration
            currrent_time = 0.0
            end_time = duration
            while currrent_time < end_time:
                self._simulate_transaction()
                inter_arrival_time = self._generate_interarrival_time()
                currrent_time += inter_arrival_time
        elif num_transactions is not None:
            # Simulate based on number of transactions
            for _ in range(num_transactions):
                self._simulate_transaction()
                inter_arrival_time = self._generate_interarrival_time()


# # ======================== Example Usage ========================
# if __name__ == "__main__":
#     # Initialize the TransactionSimulator
#     simulator = TransactionSimulator(
#         num_accounts=10,
#         balance_sampler_config=BalanceSamplerConfig(balance_type="uniform", uniform_low=1, uniform_high=100),
#         chain_id=1337,
#         output_dir="./data",
#         client_type="reth",
#         rpc_url="http://127.0.0
#     )

#     # Run the simulation for a specific duration
#     simulator.run_simulation(duration=60)  # Run for 60 seconds

#     # Or run the simulation for a specific number of transactions
#     # simulator.run_simulation(num_transactions=100)  # Run 100 transactions
