# %%
from ethsimulator import SimulationManager
import pandas as pd

# %%
collection_metrics = [
    "eth_exe_block_head_gas_used",
    "eth_exe_gas_price_gwei",
    "network_node_bytes_total_received",
    "cpu_iowait_seconds_total",
    "disk_node_reads_total",
    "process_cpu_seconds_total",
    "eth_exe_block_head_transactions_in_block"
    "cpu_idle_seconds_total",
    "cpu_system_seconds_total",
    "cpu_user_seconds_total",
    "cpu_threads",
    "disk_node_writes_total"
]

# %%
parameter_sweep = pd.DataFrame({
    "spamoor_extra_args": [{"amount": 20, "count": 2000}] * 6,
    "spamoor_max_wallets": 20,
    "spamoor_throughput": 20000,
    "el_clients": [['geth'], ['erigon'], ['nethermind'], ['besu'], ['reth'], ['ethereumjs']],
    "cl_clients": [['lighthouse']] * 6,
})

parameter_sweep = parameter_sweep.merge(
    pd.DataFrame({
        "spamoor_scenario": ["eoatx", "erctx", "deploy-destruct"]
    }),
    how="cross"
)

parameter_sweep["enclave_name"] = parameter_sweep[["el_clients", "spamoor_scenario"]].apply(lambda x: f"singlenode-{x['spamoor_scenario']}-{x['el_clients'][0]}", axis=1)

duration = 5 * 60

parameter_sweep

# %%
sim = SimulationManager(results_dir="./results")
for _, row in parameter_sweep.iterrows():
    print(row)
    config_file = sim.generate_config(
        enclave_name=row["enclave_name"],
        el_clients=row["el_clients"],
        cl_clients=row["cl_clients"],
        spamoor_scenario=row["spamoor_scenario"],
        spamoor_max_wallets=row["spamoor_max_wallets"],
        spamoor_throughput=row["spamoor_throughput"],
        spamoor_extra_args=row["spamoor_extra_args"]
    )
    sim.run_simulation(timeout=600, duration=300, collected_metrics=collection_metrics)
