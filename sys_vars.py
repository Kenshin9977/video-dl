import logging
from utils.sys_utils import get_ff_components_path, get_system_architecture

logger = logging.getLogger()

FF_PATH = get_ff_components_path()
ARCHITECTURE = get_system_architecture()

logger.debug("FF_PATH: %s", FF_PATH)
logger.debug("ARCHITECTURE: %s", ARCHITECTURE)
