"""
App Navigation (Frontend Command Dispatch) Tool
===============================================

Handles sending structured JSON commands back to the React frontend
via Websocket or SSE to control the user's screen natively without reloading.
"""

import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class AppNavigationTool:
    """Tool to control the user's React frontend."""

    def __init__(self):
        pass

    async def execute(
        self,
        action: str,
        target: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a command payload that the API layer will intercept and broadcast
        to the client via Websockets/SSE.

        Args:
            action: Command type (e.g. 'navigate', 'open_modal', 'apply_filters')
            target: The route (e.g. '/pipeline', '/brief') or modal ID
            filters: Optional dictionary mapping filter names to values

        Returns:
            JSON string payload confirming the dispatch instruction
        """
        logger.info(f"[TOOL] app_navigation: action='{action}' target='{target}'")

        try:
            payload = {
                "action": action,
                "target": target,
                "filters": filters or {}
            }
            
            # The agent return block itself serves as the payload. When the API endpoint
            # parses the tool response, if it sees a `__FRONTEND_COMMAND__` tag or 
            # recognizes this structured response, it will emit the socket event.
            
            wrapped_response = {
                "status": "success",
                "message": f"I have successfully navigated your screen to {target or 'the requested destination'}.",
                "__FRONTEND_COMMAND__": payload
            }
            
            return json.dumps(wrapped_response)
            
        except Exception as e:
            logger.error(f"[TOOL] app_navigation error: {e}")
            return json.dumps({
                "status": "error",
                "message": f"Failed to dispatch frontend command: {type(e).__name__}: {e}"
            })
