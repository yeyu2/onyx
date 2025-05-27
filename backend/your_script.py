from onyx.utils.logger import setup_logger

# Create a logger with your module name
logger = setup_logger(__name__)

# Use different log levels
logger.debug("This is a debug message")
logger.info("This is an info message")
logger.notice("This is a notice message")  # Custom level between INFO and WARNING
logger.warning("This is a warning message")
logger.error("This is an error message")
logger.critical("This is a critical message")

# Don't use print() as it won't show up properly
# print("This won't work reliably")  # Not recommended 