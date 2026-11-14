import logging

# Create a logger for the application
logger = logging.getLogger("stegchat")
logger.setLevel(logging.INFO)

# Console handler with a simple formatter
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

# Ensure logger does not propagate to root logger
logger.propagate = False

