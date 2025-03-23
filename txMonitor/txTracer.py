
from web3 import Web3
import sys
from collections import Counter

def main(tx_hash):
    # Replace with your own Sepolia RPC URL.
    # If you're using Infura, insert your Project ID.
    rpc_url = "USE YOUR OWN RPC URL HERE"
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    # Check connection
    if not w3.is_connected():
        print("Error: Unable to connect to the Sepolia node.")
        return

    # Use debug_traceTransaction to get the execution trace
    try:
        trace_response = w3.provider.make_request("debug_traceTransaction", [tx_hash, {}])
    except Exception as e:
        print("Exception while calling debug_traceTransaction:", e)
        return

    if "error" in trace_response:
        print("Error fetching trace:", trace_response["error"])
        return

    # Extract trace logs
    struct_logs = trace_response.get("result", {}).get("structLogs", [])

    # print(struct_logs   )
    if not struct_logs:
        print("No trace logs found for the given transaction.")
        return

    # Count occurrences of each opcode using Counter
    opcode_counter = Counter(log.get("op") for log in struct_logs if "op" in log)

    return opcode_counter

    # print(f"Number of unique opcodes: {len(opcode_counter)}")
    # print("Opcode occurrences (most frequent to least):")
    # for opcode, count in sorted(opcode_counter.items(), key=lambda x: x[1], reverse=True):
    #     print(f"{opcode}: {count}")





if __name__ == "__main__":

    txHashes = [
        "0x8832f34e63d2d2c772d8d0b2782f8832ada45e008adeca336a2fa5f61bd5ef40", \
        "0x80f98ecb4ccf12474e3e8efc418eedcee4500f5387600ad2ba62f03f1245289c", \
        "0xc5301abe12c3b6005ad18ee92d9abd615ed0a9a35dec6b10749a3e0161e80030", \
        "0x107c1a9552157aa66d77021d36c4c1a22f4f018105cc748b7e9735eb89439033", \
        "0xc441130a448923d6d92a019d4e898e2e1a073cfbac81a011bdf34f16e7a62e76", \
        "0x4166f5f9c5ba779d3f09303203c1957a76a5b329afc2844c2facb2b409e818e0",
    ]
    total_opcode_counter = Counter()
    for txHash in txHashes:
        opcode_counter = main(txHash)
        if opcode_counter:
            total_opcode_counter += opcode_counter

    # all values in total_opcode_counter divided by the number of transactions
    print("Total opcode occurrences across all transactions:")
    for opcode, count in sorted(total_opcode_counter.items(), key=lambda x: x[1], reverse=True):
        # round to the nearest integer
        count_int = round(count / len(txHashes))
        print(f"{opcode}: {count_int}")


    




