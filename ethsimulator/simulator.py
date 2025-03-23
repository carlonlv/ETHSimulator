import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
import time
from typing import Any, Dict, List, Literal, Optional

import matplotlib.pyplot as plt
import pandas as pd
import yaml
from prometheus_api_client import PrometheusConnect  # type: ignore[import-untyped]
from pydantic import BaseModel, Field, PrivateAttr

IMAGE_MAPPER = {
    "geth": "ethereum/client-go:latest",
    "erigon": "ethpandaops/erigon:main",
    "nethermind": "nethermind/nethermind:latest",
    "besu": "hyperledger/besu:develop",
    "reth": "ghcr.io/paradigmxyz/reth",
    "ethereumjs": "ethpandaops/ethereumjs:master",
    "nimbus-eth1": "ethpandaops/nimbus-eth1:master",
    "lighthouse": "sigp/lighthouse:latest",
    "teku": "consensys/teku:latest",
    "nimbus": "statusim/nimbus-eth2:multiarch-latest",
    "prysm": "gcr.io/prysmaticlabs/prysm/beacon-chain:latest",
    "lodestar": "chainsafe/lodestar:next",
    "grandine": "sifrai/grandine:stable",
}


class SimulationManager(BaseModel):
    results_dir: str = Field("./", description="Directory to save simulation results.")

    _enclave_name: str = PrivateAttr()
    _config_path: str = PrivateAttr()
    _prometheus: PrometheusConnect = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization method.

        :param __context: Any - The context object.
        :type __context: Any
        """
        os.makedirs(self.results_dir, exist_ok=True)

    def generate_config(
        self,
        enclave_name: Optional[str] = None,
        el_clients: List[Literal["geth", "erinon", "nethermind", "besu", "reth", "ethereumjs", "nimbus-eth1"]] = ["geth"],
        cl_clients: List[Literal["lighthouse", "teku", "nimbus", "prysm", "lodestar", "grandine"]] = ["lighthouse"],
        spamoor_scenario: Literal["eoatx", "erctx", "deploytx", "deploy-destruct", "blobs", "gasburnertx"] = "eoatx",
        spamoor_throughput: int = 1000,
        spamoor_max_pending: int = 1000,
        spamoor_max_wallets: int = 500,
        spamoor_extra_args: Dict[str, Any] = {},
        prometheus_scape_interval: str = "15s",
        prometheus_labels: Dict[str, Any] = {},
    ) -> str:
        """Generates a configuration file for the Ethereum network simulation.

        :param enclave_name: The name of the enclave to use for the simulation, defaults to None
        :type enclave_name: Optional[str]
        :param el_clients: A list of Ethereum execution clients to use in the simulation, defaults to ["geth"]
        :type el_clients: List[Literal["geth", "erinon", "nethermind", "besu", "reth", "ethereumjs", "nimbus-eth1"]]
        :param cl_clients: A list of Ethereum consensus clients to use in the simulation, defaults to ["lighthouse"]
        :type cl_clients: List[Literal["lighthouse", "teku", "nimbus", "prysm", "lodestar", "grandine"]]
        :param spamoor_scenario: The spamoor scenario to use in the simulation, defaults to "eoatx"
        :type spamoor_scenario: Literal["eoatx", "erctx", "deploytx", "deploy-destruct", "blobs", "gasburnertx"]
        :param spamoor_throughput: The throughput of the spamoor scenario, defaults to 1000
        :type spamoor_throughput: int
        :param spamoor_max_pending: The maximum number of pending transactions in the spamoor scenario, defaults to 1000
        :type spamoor_max_pending: int
        :param spamoor_max_wallets: The maximum number of wallets in the spamoor scenario, defaults to 500
        :type spamoor_max_wallets: int
        :param spamoor_extra_args: A dictionary of extra arguments to pass to spamoor, defaults to {}
        :type spamoor_extra_args: Dict[str, Any]
        :param prometheus_scape_interval: The Prometheus scrape interval, defaults to "15s"
        :type prometheus_scape_interval: str
        :param prometheus_labels: A dictionary of Prometheus labels, defaults to {}
        :type prometheus_labels: Dict[str, Any]
        :return: The path to the generated configuration file.
        :rtype: str
        """
        assert len(el_clients) > 0, "At least one execution client must be specified."
        assert len(el_clients) == len(cl_clients), "The number of execution clients must match the number of consensus clients."

        participants = [
            {
                "el_type": el_client,
                "el_image": IMAGE_MAPPER[el_client],
                "el_log_level": "",
                # A list of optional extra env_vars the el container should spin up with
                "el_extra_env_vars": {},
                # A list of optional extra labels the el container should spin up with
                # Example; el_extra_labels: {"ethereum-package.partition": "1"}
                "el_extra_labels": {},
                # A list of optional extra params that will be passed to the EL client container for modifying its behaviour
                "el_extra_params": [],
                # A list of tolerations that will be passed to the EL client container
                # Only works with Kubernetes
                # Example: el_tolerations:
                # - key: "key"
                #   operator: "Equal"
                #   value: "value"
                #   effect: "NoSchedule"
                #   toleration_seconds: 3600
                # Defaults to empty
                "el_tolerations": [],
                # Persistent storage size for the EL client container (in MB)
                # Defaults to 0, which means that the default size for the client will be used
                # Default values can be found in /src/package_io/constants.star VOLUME_SIZE
                "el_volume_size": 0,
                # Resource management for el containers
                # CPU is milicores
                # RAM is in MB
                # Defaults to 0, which results in no resource limits
                "el_min_cpu": 0,
                "el_max_cpu": 0,
                "el_min_mem": 0,
                "el_max_mem": 0,
                # CL(Consensus Layer) Specific flags
                # The type of CL client that should be started
                # Valid values are nimbus, lighthouse, lodestar, teku, prysm, and grandine
                "cl_type": cl_client,
                # The Docker image that should be used for the CL client; leave blank to use the default for the client type
                # Defaults by client:
                # - lighthouse: sigp/lighthouse:latest
                # - teku: consensys/teku:latest
                # - nimbus: statusim/nimbus-eth2:multiarch-latest
                # - prysm: gcr.io/prysmaticlabs/prysm/beacon-chain:latest
                # - lodestar: chainsafe/lodestar:next
                # - grandine: sifrai/grandine:stable
                "cl_image": "",
                # The log level string that this participant's CL client should log at
                # If this is emptystring then the global `logLevel` parameter's value will be translated into a string appropriate for the client (e.g. if
                # global `logLevel` = `info` then Teku would receive `INFO`, Prysm would receive `info`, etc.)
                # If this is not emptystring, then this value will override the global `logLevel` setting to allow for fine-grained control
                # over a specific participant's logging
                "cl_log_level": "",
                # A list of optional extra env_vars the cl container should spin up with
                "cl_extra_env_vars": {},
                # A list of optional extra labels that will be passed to the CL client Beacon container.
                # Example; cl_extra_labels: {"ethereum-package.partition": "1"}
                "cl_extra_labels": {},
                # A list of optional extra params that will be passed to the CL client Beacon container for modifying its behaviour
                # If the client combines the Beacon & validator nodes (e.g. Teku, Nimbus), then this list will be passed to the combined Beacon-validator node
                "cl_extra_params": [],
                # A list of tolerations that will be passed to the CL client container
                # Only works with Kubernetes
                # Example: el_tolerations:
                # - key: "key"
                #   operator: "Equal"
                #   value: "value"
                #   effect: "NoSchedule"
                #   toleration_seconds: 3600
                # Defaults to empty
                "cl_tolerations": [],
                # Persistent storage size for the CL client container (in MB)
                # Defaults to 0, which means that the default size for the client will be used
                # Default values can be found in /src/package_io/constants.star VOLUME_SIZE
                "cl_volume_size": 0,
                # Resource management for cl containers
                # CPU is milicores
                # RAM is in MB
                # Defaults to 0, which results in no resource limits
                "cl_min_cpu": 0,
                "cl_max_cpu": 0,
                "cl_min_mem": 0,
                "cl_max_mem": 0,
            }
            for el_client, cl_client in zip(el_clients, cl_clients)
        ]

        spamoor_params = {
            "image": "ethpandaops/spamoor:latest",
            "scenario": spamoor_scenario,
            "throughput": spamoor_throughput,
            "max_pending": spamoor_max_pending,
            "max_wallets": spamoor_max_wallets,
            "spamoor_extra_args": [f"--{k}={str(v)}" for k, v in spamoor_extra_args.items()],
        }

        prometheus_config = {"scrape_interval": prometheus_scape_interval, "labels": prometheus_labels}

        config = {"participants": participants, "spamoor_params": spamoor_params, "prometheus_config": prometheus_config, "additional_services": ["spamoor", "prometheus_grafana", "dora"], "ethereum_metrics_exporter_enabled": True}

        config_json = json.dumps(config, indent=4)
        config_hash = hash(config_json)
        if enclave_name is None:
            enclave_name = f"ethereum-sim-{config_hash}"
        else:
            if enclave_name.endswith(".yaml"):
                enclave_name = enclave_name[:-5]
        self._enclave_name = enclave_name
        output_path = os.path.join(self.results_dir, f"config_{enclave_name}.yaml")
        with open(output_path, "w") as f:
            yaml.dump(config, f)
        self._config_path = output_path
        return output_path

    def _stop_simulation(self) -> None:
        """Stops the simulation."""
        process = subprocess.run(["kurtosis", "enclave", "rm", "-f", self._enclave_name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        print(process.stdout)

    def _collect_metrics(
            self,
            metric_name="up",
            duration=600,
            step="30s",
            output_csv="metrics.csv"
        ) -> None:
        """Collects metrics from Prometheus and saves them to a CSV file.
    
        :param metric_name: The name of the metric to collect, defaults to "up"
        :type metric_name: str
        :param duration_minutes: The duration of the metric collection in minutes, defaults to 10
        :type duration_minutes: int
        :param step: The step size for the metric collection, defaults to "30s"
        :type step: str
        """
        end = datetime.now(timezone.utc)
        start = end - timedelta(seconds=duration)
        data = self._prometheus.get_metric_range_data(metric_name=metric_name, start_time=start, end_time=end, step=step)
        # Convert Prometheus response to pandas DataFrame
        df_list = []
        for result in data:
            for values in result["values"]:
                ts, val = values
                df_list.append({"timestamp": datetime.utcfromtimestamp(float(ts)), "value": float(val), "metric": result["metric"]})
        df = pd.DataFrame(df_list)
        full_path = os.path.join(self.results_dir, output_csv)
        df.to_csv(full_path, index=False)
        print(f"Saved metrics to {full_path}")
        return df

    def run_simulation(
            self,
            enclave_name: Optional[str] = None,
            config_file: Optional[str] = None,
            timeout: Optional[int] = 600,
            duration: int = 600
        ) -> None:
        """Runs the simulation using the Kurtosis CLI.

        :param config_file: The path to the configuration file to use for the simulation, defaults to None
        :type config_file: Optional[str]
        :param enclave_name: The name of the enclave to use for the simulation, defaults to None
        :type enclave_name: Optional[str]
        :param timeout: The timeout for the simulation in seconds, defaults to 600
        :type timeout: Optional[int]
        :param duration: The duration of the metric collection in seconds, defaults to 600
        :type duration: int
        """
        if config_file is None:
            assert self._config_path is not None, "A configuration file must be provided."
            config_file = self._config_path
            enclave_name = self._enclave_name
        else:
            assert os.path.exists(config_file), "The configuration file does not exist."
            assert enclave_name is not None, "An enclave name must be provided."
            self._enclave_name = enclave_name
            self._config_path = config_file
    
        print(f"Running simulation with Kurtosis with config file: {config_file}")
        process = subprocess.Popen(["kurtosis", "run", "--enclave", enclave_name, "github.com/ethpandaops/ethereum-package", "--args-file", config_file], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        user_services_seen = False
        prometheus_url = None

        assert process.stdout is not None, "Failed to start Kurtosis run."
        for line in iter(process.stdout.readline, ""):
            print(line, end="")  # optional: stream output live

            if not user_services_seen and "User Services" in line:
                user_services_seen = True
                print("✅ Detected User Services section.")

            if user_services_seen and "prometheus" in line.lower():
                # Look for something like http://127.0.0.1:33164
                match = re.search(r"http://127\.0\.0\.1:\d+", line)
                if match:
                    prometheus_url = match.group()
                    print(f"📡 Found Prometheus endpoint: {prometheus_url}")
                    break

        process.wait(timeout=timeout)
        if process.returncode != 0:
            raise RuntimeError("❌ Kurtosis run failed unexpectedly before completing.")

        if not user_services_seen:
            raise RuntimeError("❌ 'User Services' section not found — simulation likely failed early.")

        if not prometheus_url:
            raise RuntimeError("❌ Prometheus URL not found in output.")

        # Update Prometheus connection for future metric collection
        self._prometheus = PrometheusConnect(url=prometheus_url, disable_ssl=True)

        # Wait for a duration to collect metrics
        print(f"Waiting for {duration} seconds to collect metrics...")
        time.sleep(duration)

        # Collect the metrics

        # Stop the simulation
        self._stop_simulation()

    def plot_metric(self, df, title="Metric Over Time"):
        if df.empty:
            print("No data to plot.")
            return
        plt.figure(figsize=(10, 5))
        plt.plot(df["timestamp"], df["value"])
        plt.xlabel("Time")
        plt.ylabel("Value")
        plt.title(title)
        plt.grid(True)
        plt.show()
