# %%
import pandas as pd

from ethsimulator import SimulationManager

##### single node test on el clients #####

# %%
collection_metrics = [
    "eth_exe_block_head_gas_used",
    "eth_exe_gas_price_gwei",
    "network_node_bytes_total_received",
    "cpu_iowait_seconds_total",
    "disk_node_reads_total",
    "process_cpu_seconds_total",
    "eth_exe_block_head_transactions_in_block",
    "cpu_idle_seconds_total",
    "cpu_system_seconds_total",
    "cpu_user_seconds_total",
    "cpu_threads",
    "disk_node_writes_total"
]

# %%
parameter_sweep = pd.DataFrame({
    "spamoor_extra_args": [{"amount": 20, "count": 2000}] * 2,
    "spamoor_max_wallets": 20,
    "spamoor_throughput": 20000,
    # "el_clients": [['geth'], ['erigon'], ['nethermind'], ['besu'], ['reth'], ['ethereumjs']],
    # erigon failed
    "el_clients": [['erigon'],['nethermind'], ],
    "cl_clients": [['lighthouse']] * 2
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
sim = SimulationManager(results_dir="./new_results_20250402")
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


######## multi nodes ##########




# def run_multi_nodes(parameter_sweep, num_nodes):
    
#     parameter_sweep = parameter_sweep.merge(
#     pd.DataFrame({
#         "spamoor_scenario": ["eoatx", "erctx", "deploy-destruct"]
#     }),
#     how="cross"
#     )

#     parameter_sweep["enclave_name"] = parameter_sweep[["el_clients", "spamoor_scenario"]].apply(lambda x: f"n-{num_nodes}-{x['spamoor_scenario']}-{x['el_clients'][0]}", axis=1)

#     duration = 5 * 60

#     parameter_sweep

#     # %%
#     sim = SimulationManager(results_dir="./new_results_20250402")
#     for _, row in parameter_sweep.iterrows():
#         print(row)
#         config_file = sim.generate_config(
#             enclave_name=row["enclave_name"],
#             el_clients=row["el_clients"],
#             cl_clients=row["cl_clients"],
#             spamoor_scenario=row["spamoor_scenario"],
#             spamoor_max_wallets=row["spamoor_max_wallets"],
#             spamoor_throughput=row["spamoor_throughput"],
#             spamoor_extra_args=row["spamoor_extra_args"]
#         )
#         sim.run_simulation(timeout=600, duration=300, collected_metrics=collection_metrics)




## multi nodes but each node has the same cl and el clients

# %%
# n = 5
# parameter_sweep = pd.DataFrame({
#     "spamoor_extra_args": [{"amount": 20, "count": 2000}],
#     "spamoor_max_wallets": 20,
#     "spamoor_throughput": 20000,
#     "el_clients": [['geth']*n],
#     "cl_clients": [['lighthouse'] * n]
# })

# run_multi_nodes(parameter_sweep, n)


# n = 10
# parameter_sweep = pd.DataFrame({
#     "spamoor_extra_args": [{"amount": 20, "count": 2000}],
#     "spamoor_max_wallets": 20,
#     "spamoor_throughput": 20000,
#     "el_clients": [['geth']*n],
#     "cl_clients": [['lighthouse'] * n]
# })

# run_multi_nodes(parameter_sweep, n)

# n = 15
# parameter_sweep = pd.DataFrame({
#     "spamoor_extra_args": [{"amount": 20, "count": 2000}],
#     "spamoor_max_wallets": 20,
#     "spamoor_throughput": 20000,
#     "el_clients": [['geth']*n],
#     "cl_clients": [['lighthouse'] * n]
# })

# run_multi_nodes(parameter_sweep, n)



###### diff clients ########

# def run_multi_nodes_vary_cl(cl_client, num_nodes=5):
    
#     parameter_sweep = pd.DataFrame({
#     "spamoor_extra_args": [{"amount": 20, "count": 2000}],
#     "spamoor_max_wallets": 20,
#     "spamoor_throughput": 20000,
#     "el_clients": [['geth']*n],
#     "cl_clients": [[cl_client]*n]
#     })
    
#     parameter_sweep = parameter_sweep.merge(
#     pd.DataFrame({
#         "spamoor_scenario": ["eoatx", "erctx", "deploy-destruct"]
#     }),
#     how="cross"
#     )

#     parameter_sweep["enclave_name"] = parameter_sweep[["el_clients", "spamoor_scenario"]].apply(lambda x: f"n-{num_nodes}-cl-{cl_client}-{x['spamoor_scenario']}-{x['el_clients'][0]}", axis=1)

#     duration = 5 * 60

#     parameter_sweep

#     # %%
#     sim = SimulationManager(results_dir="./new_results_20250402")
#     for _, row in parameter_sweep.iterrows():
#         print(row)
#         config_file = sim.generate_config(
#             enclave_name=row["enclave_name"],
#             el_clients=row["el_clients"],
#             cl_clients=row["cl_clients"],
#             spamoor_scenario=row["spamoor_scenario"],
#             spamoor_max_wallets=row["spamoor_max_wallets"],
#             spamoor_throughput=row["spamoor_throughput"],
#             spamoor_extra_args=row["spamoor_extra_args"]
#         )
#         sim.run_simulation(timeout=600, duration=300, collected_metrics=collection_metrics)

# n = 5
# run_multi_nodes_vary_cl('teku')
# run_multi_nodes_vary_cl('prysm')
# run_multi_nodes_vary_cl('nimbus')

# grandine failed
# run_multi_nodes_vary_cl('grandine')

# run_multi_nodes_vary_cl('lighthouse')
# run_multi_nodes_vary_cl('lodestar')

