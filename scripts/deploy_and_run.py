from brownie import (
    Box,
    MyToken,
    MyGovernor,
    GovernanceTimeLock,
    network,
    config,
    chain,
    accounts
)

from .helpers import get_account, encode_function_data, LOCAL_ENVIRONMENTS, FORKED_LOCAL_ENVIROMENT

from web3 import Web3, constants
import hashlib

# Governor Contract
QUORUM_PERCENTAGE = 4
# VOTING_PERIOD = 45818  # 1 week - more traditional.
# You might have different periods for different kinds of proposals
VOTING_PERIOD = 5  # 5 blocks
VOTING_DELAY = 1  # 5 block

# Timelock
# MIN_DELAY = 3600  # 1 hour - more traditional
MIN_DELAY = 3600  # 1 seconds

# Proposal
NEW_STORE_VALUE = 5
PROPOSAL_DESCRIPTION = f"Proposal #1: Store {NEW_STORE_VALUE} in the Box!"


PROPOSAL_THRESHOLD = 0


def deploy_my_token():
    account = get_account()
    MyToken.deploy(
        {'from': account},
        publish_source=config["networks"][network.show_active()].get(
            "verify", False
        ),
    )
    MyToken[-1].delegate(account)
    MyToken[-1].mintNft()


def deploy_governance_time_lock():
    GovernanceTimeLock.deploy(
        MIN_DELAY,
        [],
        [],
        get_account(),
        {'from': get_account()},
        publish_source=config["networks"][network.show_active()].get(
            "verify", False
        ),
    )


def deploy_my_governance():
    if not (MyToken):
        deploy_my_token()

    if not (GovernanceTimeLock):
        deploy_governance_time_lock()
    MyGovernor.deploy(
        MyToken[-1],
        GovernanceTimeLock[-1],
        VOTING_DELAY,
        VOTING_PERIOD,
        PROPOSAL_THRESHOLD,
        QUORUM_PERCENTAGE,
        {'from': get_account()},
        publish_source=config["networks"][network.show_active()].get(
            "verify", False
        ),
    )


def set_access_control_timeLock():
    account = get_account()
    if not (MyToken):
        deploy_my_token()

    if not (GovernanceTimeLock):
        deploy_governance_time_lock()

    if not (MyGovernor):
        deploy_my_governance()
    governance_time_lock = GovernanceTimeLock[-1]
    proposer_role = governance_time_lock.PROPOSER_ROLE()
    executor_role = governance_time_lock.EXECUTOR_ROLE()
    timelock_admin_role = governance_time_lock.TIMELOCK_ADMIN_ROLE()

    governance_time_lock.grantRole(
        proposer_role, MyGovernor[-1], {"from": account})
    governance_time_lock.grantRole(
        executor_role, constants.ADDRESS_ZERO, {"from": account}
    )
    tx = governance_time_lock.revokeRole(
        timelock_admin_role, account, {"from": account}
    )
    tx.wait(1)


def deploy_box_to_be_governed():
    account = get_account()
    box = Box.deploy({"from": account})
    tx = Box[-1].transferOwnership(GovernanceTimeLock[-1], {"from": account})
    tx.wait(1)


def create_proposal():

    tx_propose = MyGovernor[-1].propose(
        [Box[-1].address],
        [0],
        [encode_function_data(Box[-1].setValue, NEW_STORE_VALUE)],
        PROPOSAL_DESCRIPTION,
        {"from": get_account()}
    )
    if network.show_active() in LOCAL_ENVIRONMENTS or network.show_active() in FORKED_LOCAL_ENVIROMENT:
        chain.mine(VOTING_DELAY+1)
    tx_propose.wait(2)
    return tx_propose.events['ProposalCreated']['proposalId']


def vote_proposal(proposal_id: int, vote: int):
    print(f"state1.4 = {MyGovernor[-1].state(proposal_id)}")
    tx_vote = MyGovernor[-1].castVoteWithReason(
        proposal_id, vote, "yeah thats it.", {"from": get_account()}
    )
    tx_vote.wait(1)
    chain.mine(VOTING_PERIOD+1)
    print(tx_vote.events["VoteCast"])


def queue_proposal():
    description_hash = Web3.keccak(PROPOSAL_DESCRIPTION.encode('utf-8')).hex()
    tx_queue = MyGovernor[-1].queue(
        [Box[-1].address],
        [0],
        [encode_function_data(Box[-1].setValue, NEW_STORE_VALUE)],
        description_hash,
        {"from": get_account()}
    )
    tx_queue.wait(1)
    if network.show_active() in LOCAL_ENVIRONMENTS or network.show_active() in FORKED_LOCAL_ENVIROMENT:
        chain.sleep(MIN_DELAY+1)
        chain.mine(VOTING_DELAY+1)


def execute_proposal():
    description_hash = Web3.keccak(PROPOSAL_DESCRIPTION.encode('utf-8')).hex()
    tx_execute = MyGovernor[-1].execute(
        [Box[-1].address],
        [0],
        [encode_function_data(Box[-1].setValue, NEW_STORE_VALUE)],
        description_hash,
        {"from": get_account()}
    )
    tx_execute.wait(1)


def move_blocks(amount):
    for block in range(amount):
        get_account().transfer(get_account(), "0 ether")
    print(chain.height)


def main():

    deploy_my_governance()
    set_access_control_timeLock()
    deploy_box_to_be_governed()
    proposal_id = create_proposal()
    print(f"state after propose = {MyGovernor[-1].state(proposal_id)}")

    vote_proposal(proposal_id, 1)

    print(f"state after vote = {MyGovernor[-1].state(proposal_id)}")
    queue_proposal()
    print(f"state after queue = {MyGovernor[-1].state(proposal_id)}")
    execute_proposal()
    print(f"state after execute = {MyGovernor[-1].state(proposal_id)}")
    print('break')
