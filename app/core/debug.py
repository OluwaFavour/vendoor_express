import logging

# Configuring the logger
logging.basicConfig(filename="app.log", filemode="w")

# Creating an object
logger = logging.getLogger()

# Setting the threshold of logger to WARNING
logger.setLevel(logging.INFO)
