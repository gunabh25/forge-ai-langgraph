"""
ForgeAI Plugin SDK.

This module provides the necessary tools for developers to create and register
custom agents (plugins) within the ForgeAI ecosystem.
"""

import logging
from typing import Type, Optional, List, Callable
from agents.base import BaseAgent
from core.agent_registry import AgentRegistry

logger = logging.getLogger("core.plugins.sdk")

def register_plugin(
    name: Optional[str] = None,
    description: Optional[str] = None,
    capabilities: Optional[List[str]] = None,
    requires: Optional[List[str]] = None,
    produces: Optional[List[str]] = None
) -> Callable[[Type[BaseAgent]], Type[BaseAgent]]:
    """
    Decorator to register a class as a ForgeAI plugin (agent).
    
    Args:
        name: Optional name for the agent. Overrides the class's `name` property.
        description: Optional description. Overrides the class's `description` property.
        capabilities: Optional list of capabilities. Overrides the class's `capabilities` property.
        requires: Optional list of required inputs. Overrides the class's `requires` property.
        produces: Optional list of outputs. Overrides the class's `produces` property.
    """
    def decorator(cls: Type[BaseAgent]) -> Type[BaseAgent]:
        # Validation: Must inherit from BaseAgent
        if not issubclass(cls, BaseAgent):
            raise TypeError(f"Plugin class '{cls.__name__}' must inherit from BaseAgent.")
            
        # Validation: Must implement a 'run' method
        if not hasattr(cls, 'run') or not callable(getattr(cls, 'run')):
            raise TypeError(f"Plugin class '{cls.__name__}' must implement a 'run' method.")
            
        # Optional metadata injection (overriding defaults if provided)
        if name is not None:
            cls.name = property(lambda self: name)
        if description is not None:
            cls.description = property(lambda self: description)
        if capabilities is not None:
            cls.capabilities = property(lambda self: capabilities)
        if requires is not None:
            cls.requires = property(lambda self: requires)
        if produces is not None:
            cls.produces = property(lambda self: produces)
            
        # Instantiate and register the plugin
        try:
            # We assume plugins have a no-argument constructor or handle their own dependencies
            instance = cls()
            AgentRegistry().register(instance)
            logger.info(f"Successfully registered plugin: {instance.name}")
        except Exception as e:
            logger.error(f"Failed to instantiate and register plugin {cls.__name__}: {e}")
            raise
            
        return cls
        
    return decorator
