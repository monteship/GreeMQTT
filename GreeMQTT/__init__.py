from GreeMQTT.device_db import init_db
from loguru import logger

init_db()
logger.info("GreeMQTT package initialized.")
