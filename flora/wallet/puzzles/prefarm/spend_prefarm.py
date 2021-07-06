import asyncio

from blspy import G2Element
from clvm_tools import binutils

from flora.consensus.block_rewards import calculate_base_farmer_reward, calculate_pool_reward
from flora.rpc.full_node_rpc_client import FullNodeRpcClient
from flora.types.blockchain_format.program import Program
from flora.types.coin_solution import CoinSolution
from flora.types.condition_opcodes import ConditionOpcode
from flora.types.spend_bundle import SpendBundle
from flora.util.bech32m import decode_puzzle_hash
from flora.util.condition_tools import parse_sexp_to_conditions
from flora.util.config import load_config
from flora.util.default_root import DEFAULT_ROOT_PATH
from flora.util.ints import uint32, uint16


def print_conditions(spend_bundle: SpendBundle):
    print("\nConditions:")
    for coin_solution in spend_bundle.coin_solutions:
        result = Program.from_bytes(bytes(coin_solution.puzzle_reveal)).run(
            Program.from_bytes(bytes(coin_solution.solution))
        )
        error, result_human = parse_sexp_to_conditions(result)
        assert error is None
        assert result_human is not None
        for cvp in result_human:
            print(f"{ConditionOpcode(cvp.opcode).name}: {[var.hex() for var in cvp.vars]}")
    print("")


async def main() -> None:
    rpc_port: uint16 = uint16(8555)
    self_hostname = "localhost"
    path = DEFAULT_ROOT_PATH
    config = load_config(path, "config.yaml")
    client = await FullNodeRpcClient.create(self_hostname, rpc_port, path, config)
    try:
        farmer_prefarm = (await client.get_block_record_by_height(1)).reward_claims_incorporated[1]
        pool_prefarm = (await client.get_block_record_by_height(1)).reward_claims_incorporated[0]

        pool_amounts = int(calculate_pool_reward(uint32(0)) / 2)
        farmer_amounts = int(calculate_base_farmer_reward(uint32(0)) / 2)
        print(farmer_prefarm.amount, farmer_amounts)
        assert farmer_amounts == farmer_prefarm.amount // 2
        assert pool_amounts == pool_prefarm.amount // 2
        address1 = "xfl1t9qkx2nyuf4m9jtj5y26mtj927m5jvaxs6jqpdw5z60r0ph3qezqmrl7hj"  # Key 1
        address2 = "xfl1aq60ukq3pe3r3r6v3slqsjfymddlxk7q5jcx9uqppdxjkd3e2uksde9gjw"  # Key 2

        ph1 = decode_puzzle_hash(address1)
        ph2 = decode_puzzle_hash(address2)

        p_farmer_2 = Program.to(
            binutils.assemble(f"(q . ((51 0x{ph1.hex()} {farmer_amounts}) (51 0x{ph2.hex()} {farmer_amounts})))")
        )
        p_pool_2 = Program.to(
            binutils.assemble(f"(q . ((51 0x{ph1.hex()} {pool_amounts}) (51 0x{ph2.hex()} {pool_amounts})))")
        )

        print(f"Ph1: {ph1.hex()}")
        print(f"Ph2: {ph2.hex()}")
        assert ph1.hex() == "5941632a64e26bb2c972a115adae4557b74933a686a400b5d4169e3786f10644"
        assert ph2.hex() == "e834fe58110e62388f4c8c3e084924db5bf35bc0a4b062f0010b4d2b3639572d"

        p_solution = Program.to(binutils.assemble("()"))

        sb_farmer = SpendBundle([CoinSolution(farmer_prefarm, p_farmer_2, p_solution)], G2Element())
        sb_pool = SpendBundle([CoinSolution(pool_prefarm, p_pool_2, p_solution)], G2Element())

        print("\n\n\nConditions")
        print_conditions(sb_pool)
        print("\n\n\n")
        print("Farmer to spend")
        print(sb_pool)
        print(sb_farmer)
        print("\n\n\n")
        # res = await client.push_tx(sb_farmer)
        # res = await client.push_tx(sb_pool)

        # print(res)
        up = await client.get_coin_records_by_puzzle_hash(farmer_prefarm.puzzle_hash, True)
        uf = await client.get_coin_records_by_puzzle_hash(pool_prefarm.puzzle_hash, True)
        print(up)
        print(uf)
    finally:
        client.close()


asyncio.run(main())
