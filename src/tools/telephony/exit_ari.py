"""
Exit ARI Tool - Continue call in dialplan.

Allows AI to exit the Stasis application and return the call to the Asterisk dialplan.
"""

from typing import Dict, Any
from src.tools.base import Tool, ToolDefinition, ToolParameter, ToolCategory
from src.tools.context import ToolExecutionContext
import structlog

logger = structlog.get_logger(__name__)


class ExitARITool(Tool):
    """
    Exit ARI and continue in dialplan.
    
    Use when:
    - AI's work is complete but call should continue
    - Need to return to dialplan for additional processing
    - Want to hand off to IVR or other dialplan logic
    
    Unlike hangup_call which terminates the call, this tool returns control
    to the Asterisk dialplan.
    """
    
    def __init__(
        self,
        context: str = "default",
        extension: str = "s",
        priority: int = 1
    ):
        """
        Initialize exit_ari tool.
        
        Args:
            context: Dialplan context to continue in (default: "default")
            extension: Extension to continue at (default: "s")
            priority: Priority to continue at (default: 1)
        """
        self.default_context = context
        self.default_extension = extension
        self.default_priority = priority
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="exit_ari",
            description=(
                "Exit the AI conversation and continue the call in the Asterisk dialplan. "
                "Use this tool when:\\n"
                "- Your work is complete but the call should continue\\n"
                "- The caller needs to be transferred to an IVR or menu\\n"
                "- Additional dialplan processing is required\\n"
                "IMPORTANT: This does NOT hang up the call. The call will continue in the dialplan.\\n"
                "If you want to end the call completely, use hangup_call instead."
            ),
            category=ToolCategory.TELEPHONY,
            requires_channel=True,
            max_execution_time=5,
            parameters=[
                ToolParameter(
                    name="farewell_message",
                    type="string",
                    description="Optional farewell message to speak before exiting. If not provided, exits silently.",
                    required=False
                ),
                ToolParameter(
                    name="context",
                    type="string",
                    description=f"Dialplan context to continue in (default: {self.default_context})",
                    required=False
                ),
                ToolParameter(
                    name="extension",
                    type="string",
                    description=f"Extension to continue at (default: {self.default_extension})",
                    required=False
                ),
                ToolParameter(
                    name="priority",
                    type="integer",
                    description=f"Priority to continue at (default: {self.default_priority})",
                    required=False
                )
            ]
        )
    
    async def execute(
        self,
        parameters: Dict[str, Any],
        context: ToolExecutionContext
    ) -> Dict[str, Any]:
        """
        Exit ARI and continue in dialplan.
        
        Args:
            parameters: {
                farewell_message: Optional[str],
                context: Optional[str],
                extension: Optional[str],
                priority: Optional[int]
            }
            context: Tool execution context
        
        Returns:
            {
                status: "success" | "error",
                message: str,
                will_exit: bool,
                dialplan_location: str
            }
        """
        if not context.ari_client:
            logger.error("No ARI client available for exit_ari", call_id=context.call_id)
            return {
                "status": "error",
                "message": "Cannot exit ARI: no ARI client available",
                "will_exit": False
            }
        
        if not context.caller_channel_id:
            logger.error("No caller channel ID for exit_ari", call_id=context.call_id)
            return {
                "status": "error",
                "message": "Cannot exit ARI: no channel ID",
                "will_exit": False
            }
        
        # Get parameters with defaults
        farewell = parameters.get('farewell_message', '')
        dialplan_context = parameters.get('context') or self.default_context
        dialplan_extension = parameters.get('extension') or self.default_extension
        dialplan_priority = parameters.get('priority') or self.default_priority
        
        dialplan_location = f"{dialplan_context},{dialplan_extension},{dialplan_priority}"
        
        logger.info(
            "🚪 Exit ARI requested",
            call_id=context.call_id,
            channel_id=context.caller_channel_id,
            dialplan=dialplan_location,
            has_farewell=bool(farewell)
        )
        
        try:
            # Continue in dialplan
            success = await context.ari_client.continue_in_dialplan(
                context.caller_channel_id,
                context=dialplan_context,
                extension=dialplan_extension,
                priority=dialplan_priority
            )
            
            if success:
                logger.info(
                    "✅ Successfully exited ARI to dialplan",
                    call_id=context.call_id,
                    dialplan=dialplan_location
                )
                
                message = farewell if farewell else f"Continuing in dialplan at {dialplan_location}"
                
                return {
                    "status": "success",
                    "message": message,
                    "will_exit": True,
                    "ai_should_speak": bool(farewell),
                    "dialplan_location": dialplan_location
                }
            else:
                logger.error(
                    "❌ Failed to exit ARI",
                    call_id=context.call_id,
                    dialplan=dialplan_location
                )
                return {
                    "status": "error",
                    "message": "Failed to exit ARI",
                    "will_exit": False
                }
                
        except Exception as e:
            logger.error(
                "Error exiting ARI",
                call_id=context.call_id,
                error=str(e),
                exc_info=True
            )
            return {
                "status": "error",
                "message": f"Error exiting ARI: {str(e)}",
                "will_exit": False,
                "error": str(e)
            }
