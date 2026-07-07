from datetime import datetime
import os
import yaml
import random
import logging

logger = logging.getLogger(__name__)

from .utils import split_into_parts, fetch_next_best_obs_unit, fetch_obs_unit_alternatives

random.seed(int(datetime.now().timestamp()))


def dummy_handler(t0, t1, policy_config={}):
    dt = abs(t1.timestamp() - t0.timestamp())  # too lazy to check for t1<t0 now
    # get current time as a timestamp string
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    n = random.randint(1, 10)
    parts = split_into_parts(dt, n)
    commands = ["import time", f"# {now}"]
    for i, part in enumerate(parts):
        commands += [f"time.sleep({part:.2f})"]
    commands = "\n".join(commands)
    return commands


def ops_db_handler(t0, t1, policy_config={}):
    """Handler that fetches the next best obs unit from ops-db-api and returns an observation script.

    Fetches next_best and next_alternatives from {OPS_DB_API_URL}/scheduler/,
    merges with user-defined params from policy_config, writes obs_config.yaml
    into SCHED_SCRIPTS_DIR, then returns a dict with:
        commands: str  - contents of observation.py
        next_best: dict
        next_alternatives: dict
    """
    next_best = fetch_next_best_obs_unit(os.environ.get('OPS_DB_API_URL'), os.environ.get('OPS_DB_API_TOKEN'))
    next_alternatives = fetch_obs_unit_alternatives(os.environ.get('OPS_DB_API_URL'), os.environ.get('OPS_DB_API_TOKEN'))
    logger.info(f"Next best obs unit: {next_best!r}")

    obs_config = {
        'obs_unit_name': next_best.get('obs_unit_name'),
        'start_time': next_best.get('start_time'),
        'elevation': next_best.get('best_elevation'),
        'home_at_end': policy_config.get('home_at_end', False),
        'instrument_config': policy_config.get('instrument_config', 'no_retuning'),
        't_sec': policy_config.get('t_sec', 1800),
        'az_speed': policy_config.get('az_speed', 1.0),
    }
    logger.info(f"obs_config: {obs_config!r}")

    config_path = os.path.join(os.environ['SCHED_SCRIPTS_DIR'], 'obs_config.yaml')
    with open(config_path, 'w') as f:
        yaml.dump(obs_config, f, default_flow_style=False)
    logger.info(f"Wrote obs_config to {config_path}")

    script_path = os.path.join(os.environ['SCHED_SCRIPTS_DIR'], 'observation.py')
    with open(script_path) as f:
        commands = f.read()

    return {
        'commands': commands,
        'next_best': next_best,
        'next_alternatives': next_alternatives,
    }

HANDLERS = {
    'dummy': dummy_handler,
    'ops_db': ops_db_handler,
}

def get_handler(policy_name):
    assert policy_name in HANDLERS, f"Unknown policy {policy_name}"
    return HANDLERS[policy_name]
