"""
Exit ARI Tool - Continue call in dialplan.

Allows AI to exit the Stasis application and return the call to the Asterisk dialplan.
"""

from typing import Dict, Any, Optional
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
    """
    
    def __init__(
        self,
        name: str = "exit_ari",
        context: str = "default",
        extension: str = "s",
        priority: int = 1,
        variables: Optional[Dict[str, str]] = None,
        description: Optional[str] = None
    ):
        self._name = name
        self.default_context = context
        self.default_extension = extension
        self.default_priority = priority
        self.default_variables = variables or {}
        self._custom_description = description
    
    @property
    def definition(self) -> ToolDefinition:
        desc = self._custom_description or (
            "Exit the AI conversation and continue the call in the Asterisk dialplan. "
            "Use this tool when you are done and want to return control to Asterisk."
        )
        return ToolDefinition(
            name=self._name,
            description=desc,
            category=ToolCategory.TELEPHONY,
            requires_channel=True,
            parameters=[
                ToolParameter(
                    name="farewell_message",
                    type="string",
                    description="Optional farewell message to speak before exiting.",
                    required=False
                ),
                ToolParameter(
                    name="context",
                    type="string",
                    description=f"Dialplan context (default: {self.default_context})",
                    required=False
                ),
                ToolParameter(
                    name="extension",
                    type="string",
                    description=f"Extension (default: {self.default_extension})",
                    required=False
                ),
                ToolParameter(
                    name="priority",
                    type="integer",
                    description=f"Priority (default: {self.default_priority})",
                    required=False
                ),
                ToolParameter(
                    name="variables",
                    type="object",
                    description="Custom variables to set on the channel before continuing (e.g. {'STATUS': 'COMPLETED'}).",
                    required=False
                )
            ]
        )
    
    async def execute(
        self,
        parameters: Dict[str, Any],
        context: ToolExecutionContext
    ) -> Dict[str, Any]:
        if not context.ari_client:
            return {"status": "error", "message": "No ARI client available"}
        
        channel_id = context.caller_channel_id
        if not channel_id:
            return {"status": "error", "message": "No channel ID available"}
        
        # Get parameters with defaults from constructor
        farewell = parameters.get('farewell_message', '')
        dialplan_context = parameters.get('context') or self.default_context
        dialplan_extension = parameters.get('extension') or self.default_extension
        dialplan_priority = parameters.get('priority') or self.default_priority
        
        # Merge variables: parameters override defaults
        custom_vars = self.default_variables.copy()
        if isinstance(parameters.get('variables'), dict):
            custom_vars.update(parameters['variables'])
        
        logger.info(
            "🚪 Exit ARI requested", 
            call_id=context.call_id, 
            dialplan=f"{dialplan_context},{dialplan_extension},{dialplan_priority}",
            vars=list(custom_vars.keys())
        )
        
        try:
            # Set variables first
            for var_name, var_value in custom_vars.items():
                logger.debug("Setting channel variable", channel_id=channel_id, var=var_name, val=var_value)
                await context.ari_client.set_channel_var(channel_id, var_name, str(var_value))
            
            # CRITICAL: Set transfer_active flag BEFORE calling continue_in_dialplan.
            # This prevents the engine from hanging up the caller channel when StasisEnd fires.
            await context.update_session(
                transfer_active=True,
                transfer_state="continuing_in_dialplan",
                transfer_target=f"{dialplan_context},{dialplan_extension},{dialplan_priority}"
            )
            
            # Continue in dialplan
            success = await context.ari_client.continue_in_dialplan(
                channel_id,
                context=dialplan_context,
                extension=dialplan_extension,
                priority=int(dialplan_priority)
            )
            
            if success:
                logger.info("✅ Successfully continuing in dialplan", call_id=context.call_id)
                return {
                    "status": "success",
                    "message": farewell or f"Continuing in dialplan at {dialplan_context},{dialplan_extension}",
                    "will_exit": True,
                    "ai_should_speak": bool(farewell)
                }
            return {"status": "error", "message": "Failed to exit ARI (ARI command failed)"}
            
        except Exception as e:
            logger.error("Error exiting ARI", exc_info=True)
            return {"status": "error", "message": str(e)}

def create_exit_ari_tool(tool_name: str, config: Dict[str, Any]) -> ExitARITool:
    """Factory function for metadata-driven creation from YAML."""
    return ExitARITool(
        name=tool_name,
        context=config.get('context', 'default'),
        extension=config.get('extension', 's'),
        priority=int(config.get('priority', 1)),
        variables=config.get('variables', {}),
        description=config.get('description')
    )
