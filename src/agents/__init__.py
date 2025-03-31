"""
This module contains the agent system for CLAIA.
Agents process requests and manage the conversation flow.
"""

# External dependencies
import logging

# Internal dependencies
from enums import AgentType
from .process import Process
from .queue import ProcessQueue
from .agent import Agent
from .simple import SimpleAgent
from .bob import BobAgent



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                           REGISTER AGENTS                            #
########################################################################
# Register the default agent implementations
Agent.register_agent(AgentType.SIMPLE, SimpleAgent)
Agent.register_agent(AgentType.BOB, BobAgent)
