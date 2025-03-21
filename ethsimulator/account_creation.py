import json
import os
from typing import Dict, List, Literal

import numpy as np
from eth_account import Account
from pydantic import BaseModel, Field, PositiveFloat, PositiveInt, PrivateAttr


class BalanceSamplerConfig(BaseModel):
    """
    Configuration for sampling initial balances for Ethereum accounts.
    """

    balance_type: Literal["constant", "normal", "uniform"] = Field(..., description="Method for balance assignment.")
    constant_value: PositiveFloat = Field(100 * 10**18, description="Constant balance value in Wei.")
    normal_mean: PositiveFloat = Field(100 * 10**18, description="Mean balance for normal distribution in Wei.")
    normal_std: PositiveFloat = Field(20 * 10**18, description="Standard deviation for normal distribution in Wei.")
    uniform_low: PositiveFloat = Field(50 * 10**18, description="Lower bound for uniform distribution in Wei.")
    uniform_high: PositiveFloat = Field(150 * 10**18, description="Upper bound for uniform distribution in Wei.")


class AccountCreator(BaseModel):
    """
    A class for generating Ethereum accounts and initializing balances
    for use in a Reth or Geth blockchain environment, with Pydantic validation.

    :param num_accounts: The number of Ethereum accounts to generate.
    :type num_accounts: PositiveInt
    :param balance_sampler_config: Configuration for balance sampling.
    :type balance_sampler_config: BalanceSamplerConfig
    :param chain_id: The Ethereum chain ID (default: 1337).
    :type chain_id: PositiveInt
    :param output_dir: Directory to save the generated files (default: ".").
    :type output_dir: str
    """

    num_accounts: PositiveInt = Field(..., description="Number of Ethereum accounts to generate.")
    balance_sampler_config: BalanceSamplerConfig = Field(..., description="Configuration for balance sampling.")
    chain_id: PositiveInt = Field(1337, description="Ethereum chain ID.")
    output_dir: str = Field(".", description="Directory to save generated files.")

    _accounts: List[Dict[str, str]] = PrivateAttr(default=[])
    _balances: Dict[str, Dict[str, str]] = PrivateAttr(default={})

    def generate_accounts(self) -> None:
        """Generates Ethereum accounts and assigns initial balances based on the chosen balance type."""
        match self.balance_sampler_config.balance_type:
            case "constant":
                balances = self._constant_balance()
            case "normal":
                balances = self._normal_distribution_balance()
            case "uniform":
                balances = self._uniform_distribution_balance()

        assert len(balances) == self.num_accounts, "Balance list must match number of accounts."

        for i in range(self.num_accounts):
            account = Account.create()
            self._accounts.append({"address": account.address, "private_key": account.key.hex()})
            self._balances[account.address] = {"balance": str(balances[i])}

    def _constant_balance(self) -> List[float]:
        """Assigns a constant balance to all accounts."""
        return [self.balance_sampler_config.constant_value] * self.num_accounts

    def _normal_distribution_balance(self) -> List[float]:
        """Assigns balances from a normal distribution."""
        balances = np.random.normal(loc=self.balance_sampler_config.normal_mean, scale=self.balance_sampler_config.normal_std, size=self.num_accounts).clip(min=0)
        return [float(x) for x in balances.flatten().tolist()]

    def _uniform_distribution_balance(self) -> List[float]:
        """Assigns balances from a uniform distribution."""
        return list(np.random.uniform(self.balance_sampler_config.uniform_low, self.balance_sampler_config.uniform_high, size=self.num_accounts))

    def save_to_files(self) -> None:
        """
        Saves generated Ethereum accounts and their balances to JSON files.
        Outputs:
        - `players.json`: Contains the account addresses and private keys.
        - `genesis.json`: Contains the blockchain genesis configuration with funded accounts.
        """
        players_path = os.path.join(self.output_dir, "players.json")
        with open(players_path, "w") as f:
            json.dump(self._accounts, f, indent=4)
        print(f"✅ Saved player accounts to {players_path}")

        genesis = {
            "config": {
                "chainId": self.chain_id,
                "homesteadBlock": 0,
                "eip150Block": 0,
                "eip155Block": 0,
                "eip158Block": 0,
                "byzantiumBlock": 0,
                "constantinopleBlock": 0,
                "petersburgBlock": 0,
            },
            "difficulty": "0x400",
            "gasLimit": "0x8000000",
            "alloc": self._balances,
        }

        genesis_path = os.path.join(self.output_dir, "genesis.json")
        with open(genesis_path, "w") as f:
            json.dump(genesis, f, indent=4)
        print(f"✅ Saved genesis configuration to {genesis_path}")

    def get_accounts(self) -> List[Dict[str, str]]:
        """Returns the list of generated Ethereum accounts."""
        return self._accounts


if __name__ == "__main__":
    num_players = 10  # Number of Ethereum accounts

    # Choose balance initialization method
    account_manager = AccountCreator(
        num_accounts=num_players,
        balance_sampler_config=BalanceSamplerConfig(
            balance_type="normal",  # Change to "constant" or "uniform" as needed
            normal_mean=100 * 10**18,
            normal_std=20 * 10**18
        ),
        output_dir=".",
    )

    account_manager.generate_accounts()

    # Save generated files
    account_manager.save_to_files()

    # Print generated accounts
    for acc in account_manager.get_accounts():
        print(f"Address: {acc['address']}, Private Key: {acc['private_key']}")
