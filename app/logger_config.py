# logger_config.py
import logging
import sys

def setup_logger():
    # Get a named logger instance. Using a name prevents conflicts with other libraries' loggers.
    logger = logging.getLogger("video_service")

    # Set the minimum level of messages this logger will handle (e.g., INFO, WARNING, ERROR).
    logger.setLevel(logging.INFO)

    # Create a handler to direct log messages to the console (standard output).
    handler = logging.StreamHandler(sys.stdout)

    # Define the format for the log messages.
    formatter = logging.Formatter(
        # [Timestamp] [Log Level] Logger Name - Log Message
        "[%(asctime)s] [%(levelname)s] %(name)s - %(message)s",
        # Format for the timestamp
        "%Y-%m-%d %H:%M:%S"
    )

    # Apply the defined format to the handler.
    handler.setFormatter(formatter)

    # Only add the handler if the logger doesn't already have one.
    # This prevents duplicate log messages if this setup function is called more than once.
    if not logger.handlers:
        logger.addHandler(handler)
    return logger

# Create a single, pre-configured logger instance that can be imported
# and used by any other module in the application. This ensures consistent logging.
logger = setup_logger()