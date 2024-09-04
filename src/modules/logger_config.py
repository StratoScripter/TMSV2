import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

def setup_logger(name, log_file, level=logging.ERROR):
    """Function to setup as many loggers as you want"""

    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Full path for the log file
    log_path = os.path.join(log_dir, log_file)

    formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')

    handler = RotatingFileHandler(log_path, maxBytes=10000000, backupCount=5)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

# Create a general application logger
app_logger = setup_logger('app', f'app_{datetime.now().strftime("%Y%m%d")}.log')

# Create a server module logger
server_logger = setup_logger('server', f'server_{datetime.now().strftime("%Y%m%d")}.log')

# Create a database activity logger
db_activity_logger = setup_logger('db_activity', f'db_activity_{datetime.now().strftime("%Y%m%d")}.log')

def get_logger(name):
    if name == 'app':
        return app_logger
    elif name == 'server':
        return server_logger
    elif name == 'db_activity':
        return db_activity_logger
    else:
        return setup_logger(name, f'{name}_{datetime.now().strftime("%Y%m%d")}.log')