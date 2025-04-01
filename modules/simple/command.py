"""
Simple example module demonstrating the simplified module loading system.
"""

from commands.base import Command, command
from settings import Settings
from results import Result


class SimpleCommand(Command):
    """Simple example command module."""

    @command(
        path=["hello"],
        description="Simple hello command",
        parameters={
            "type": "object",
            "properties": {}
        },
        ai_callable=True
    )
    def hello_command(self, settings: Settings) -> Result:
        """Simple hello command."""
        result = Result()
        result.message = "Hello from SimpleCommand module!"
        return result

    @command(
        path=["echo"],
        description="Echo back a message",
        parameters={
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Message to echo back"
                }
            },
            "required": ["message"]
        },
        ai_callable=True
    )
    def echo_command(self, settings: Settings, message: str) -> Result:
        """Echo back a message."""
        result = Result()
        result.message = f"Echo: {message}"
        return result