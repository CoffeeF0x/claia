"""
Agent module for the claia project.
Contains AI agents which define specific processes for managing the conversation flow.
"""

# External dependencies
import logging

# Internal dependencies
from .process import Process
from .queue import ProcessQueue
from .agent import Agent
from .simple import SimpleAgent



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                           REGISTER AGENTS                            #
########################################################################
# Register the default agent implementations
Agent.register_agent("simple", SimpleAgent)
