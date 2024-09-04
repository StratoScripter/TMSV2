import json
import os

CONFIG_FILE = 'config.json'


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {'servers': []}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def get_database_config():
    config = load_config()
    return config.get('database', {})

def save_database_config(db_config):
    config = load_config()
    config['database'] = db_config
    save_config(config)