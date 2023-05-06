from brownie import accounts, network, config
from functools import wraps
import pytest
from brownie.exceptions import VirtualMachineError
import json
LOCAL_ENVIRONMENTS = ['development', 'ganache-local']
FORKED_LOCAL_ENVIROMENT = ['mainnet-fork', 'mainnet-fork-dev']


def get_account():
    if network.show_active() in LOCAL_ENVIRONMENTS or network.show_active() in FORKED_LOCAL_ENVIROMENT:
        account = accounts[0]
    else:
        account = accounts.load("mymeta")
    return account


def deploy_with_gas(contract, *args, **kwargs):
    if network.show_active() in LOCAL_ENVIRONMENTS or network.show_active() in FORKED_LOCAL_ENVIROMENT:
        gas_price = "60 gwei"
        args[-1]['gas_price'] = gas_price
        args[-1]["gas_limit"] = 12000000
    contract.deploy(*args, **kwargs)


def only_local_env_test(func):
    from pytest import skip

    @wraps(func)
    def wrapper(*args, **kwargs):
        if network.show_active() not in LOCAL_ENVIRONMENTS:
            skip("only for local testing")
        result = func(*args, **kwargs)
        return result

    return wrapper


def call_contract_method(contract, method_name: str, *args, **kwargs):
    if network.show_active() in LOCAL_ENVIRONMENTS or network.show_active() in FORKED_LOCAL_ENVIROMENT:
        args[-1]["gas_price"] = "60 gwei"
        args[-1]["gas_limit"] = 12000000
    # args[-1]["gas_limit"] = 120000000000
    return getattr(contract, method_name)(*args, **kwargs)


def calculate_tx_fee(tx_receipt):
    return tx_receipt.gas_used*tx_receipt.gas_price


def encode_function_data(initializer=None, *args):
    """Encodes the function call so we can work with an initializer.
    Args:
        initializer ([brownie.network.contract.ContractTx], optional):
        The initializer function we want to call. Example: `box.store`.
        Defaults to None.
        args (Any, optional):
        The arguments to pass to the initializer function
    Returns:
        [bytes]: Return the encoded bytes.
    """
    if not len(args):
        args = b''

    if initializer:
        return initializer.encode_input(*args)

    return b''


def upgrade(
    account,
    proxy,
    newimplementation_address,
    proxy_admin_contract=None,
    initializer=None,
    *args
):
    transaction = None
    if proxy_admin_contract:
        if initializer:
            encoded_function_call = encode_function_data(initializer, *args)
            transaction = proxy_admin_contract.upgradeAndCall(
                proxy.address,
                newimplementation_address,
                encoded_function_call,
                {"from": account},
            )
        else:
            transaction = proxy_admin_contract.upgrade(
                proxy.address, newimplementation_address, {"from": account}
            )
    else:
        if initializer:
            encoded_function_call = encode_function_data(initializer, *args)
            transaction = proxy.upgradeToAndCall(
                newimplementation_address, encoded_function_call, {
                    "from": account}
            )
        else:
            transaction = call_contract_method(
                proxy, 'upgradeTo', newimplementation_address, {"from": account})
    return transaction
