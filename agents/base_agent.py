import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for specialized AI diagnostic agents."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming context and return structured output."""
        pass

    def execute(self, context: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], str]:
        """Safely execute agent logic with logging and exception boundary."""
        logger.info(f"[{self.name}] Beginning execution...")
        try:
            output = self.process(context)
            logger.info(f"[{self.name}] Successfully executed.")
            return True, output, ""
        except Exception as e:
            logger.error(f"[{self.name}] Execution error: {e}", exc_info=True)
            return False, {"error": str(e)}, str(e)
