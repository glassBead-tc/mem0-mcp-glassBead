"""
Dependency Injection Container

Provides a flexible dependency injection system for managing
component lifecycles and dependencies.
"""

import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union
from dataclasses import dataclass
from enum import Enum
import asyncio
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Scope(Enum):
    """Dependency scope definitions"""
    SINGLETON = "singleton"      # One instance for entire application
    REQUEST = "request"          # New instance per request
    TRANSIENT = "transient"      # New instance every time


@dataclass
class DependencyDefinition:
    """Definition of a dependency"""
    interface: Type
    implementation: Union[Type, Callable, Any]
    scope: Scope = Scope.SINGLETON
    name: Optional[str] = None
    factory: Optional[Callable] = None
    async_factory: Optional[Callable] = None
    args: List[Any] = None
    kwargs: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.args is None:
            self.args = []
        if self.kwargs is None:
            self.kwargs = {}


class Container:
    """
    Dependency injection container.
    
    Features:
    - Multiple scopes (singleton, request, transient)
    - Automatic dependency resolution
    - Circular dependency detection
    - Async support
    - Factory functions
    - Named dependencies
    """
    
    def __init__(self):
        self._definitions: Dict[Type, List[DependencyDefinition]] = {}
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
        self._resolving: set = set()  # For circular dependency detection
        self._request_scope: Dict[Type, Any] = {}
        
    def register(
        self,
        interface: Type[T],
        implementation: Union[Type[T], T, Callable[..., T]] = None,
        scope: Scope = Scope.SINGLETON,
        name: Optional[str] = None,
        factory: Optional[Callable[..., T]] = None,
        async_factory: Optional[Callable[..., T]] = None,
        **kwargs
    ) -> None:
        """
        Register a dependency.
        
        Args:
            interface: The interface/base class
            implementation: The implementation class, instance, or factory
            scope: The scope of the dependency
            name: Optional name for named dependencies
            factory: Optional factory function
            async_factory: Optional async factory function
            **kwargs: Additional arguments for construction
        """
        if implementation is None:
            implementation = interface
            
        definition = DependencyDefinition(
            interface=interface,
            implementation=implementation,
            scope=scope,
            name=name,
            factory=factory,
            async_factory=async_factory,
            kwargs=kwargs
        )
        
        if interface not in self._definitions:
            self._definitions[interface] = []
            
        # Remove existing definition with same name
        if name:
            self._definitions[interface] = [
                d for d in self._definitions[interface] 
                if d.name != name
            ]
            
        self._definitions[interface].append(definition)
        
    def register_singleton(self, interface: Type[T], implementation: Union[Type[T], T] = None, **kwargs) -> None:
        """Register a singleton dependency"""
        self.register(interface, implementation, Scope.SINGLETON, **kwargs)
        
    def register_transient(self, interface: Type[T], implementation: Union[Type[T], T] = None, **kwargs) -> None:
        """Register a transient dependency"""
        self.register(interface, implementation, Scope.TRANSIENT, **kwargs)
        
    def register_request(self, interface: Type[T], implementation: Union[Type[T], T] = None, **kwargs) -> None:
        """Register a request-scoped dependency"""
        self.register(interface, implementation, Scope.REQUEST, **kwargs)
        
    def register_factory(self, interface: Type[T], factory: Callable[..., T], scope: Scope = Scope.SINGLETON) -> None:
        """Register a factory function"""
        self.register(interface, factory=factory, scope=scope)
        
    def register_instance(self, interface: Type[T], instance: T) -> None:
        """Register an existing instance"""
        self._singletons[interface] = instance
        self.register(interface, instance, Scope.SINGLETON)
        
    async def resolve(self, interface: Type[T], name: Optional[str] = None) -> T:
        """
        Resolve a dependency.
        
        Args:
            interface: The interface to resolve
            name: Optional name for named dependencies
            
        Returns:
            The resolved instance
        """
        # Check for circular dependencies
        if interface in self._resolving:
            raise RuntimeError(f"Circular dependency detected for {interface}")
            
        self._resolving.add(interface)
        
        try:
            # Find definition
            definitions = self._definitions.get(interface, [])
            
            if not definitions:
                raise ValueError(f"No registration found for {interface}")
                
            # Find matching definition
            if name:
                definition = next((d for d in definitions if d.name == name), None)
                if not definition:
                    raise ValueError(f"No registration found for {interface} with name '{name}'")
            else:
                definition = definitions[-1]  # Use last registered
                
            # Resolve based on scope
            if definition.scope == Scope.SINGLETON:
                return await self._resolve_singleton(definition)
            elif definition.scope == Scope.REQUEST:
                return await self._resolve_request(definition)
            else:  # TRANSIENT
                return await self._resolve_transient(definition)
                
        finally:
            self._resolving.remove(interface)
            
    async def _resolve_singleton(self, definition: DependencyDefinition) -> Any:
        """Resolve a singleton dependency"""
        if definition.interface in self._singletons:
            return self._singletons[definition.interface]
            
        instance = await self._create_instance(definition)
        self._singletons[definition.interface] = instance
        return instance
        
    async def _resolve_request(self, definition: DependencyDefinition) -> Any:
        """Resolve a request-scoped dependency"""
        if definition.interface in self._request_scope:
            return self._request_scope[definition.interface]
            
        instance = await self._create_instance(definition)
        self._request_scope[definition.interface] = instance
        return instance
        
    async def _resolve_transient(self, definition: DependencyDefinition) -> Any:
        """Resolve a transient dependency"""
        return await self._create_instance(definition)
        
    async def _create_instance(self, definition: DependencyDefinition) -> Any:
        """Create an instance of a dependency"""
        # If it's already an instance, return it
        if not inspect.isclass(definition.implementation) and not callable(definition.implementation):
            return definition.implementation
            
        # Use async factory if provided
        if definition.async_factory:
            return await definition.async_factory(**definition.kwargs)
            
        # Use factory if provided
        if definition.factory:
            return definition.factory(**definition.kwargs)
            
        # If implementation is a callable (function/lambda)
        if callable(definition.implementation) and not inspect.isclass(definition.implementation):
            return definition.implementation(**definition.kwargs)
            
        # Create instance from class
        cls = definition.implementation
        
        # Resolve constructor dependencies
        sig = inspect.signature(cls.__init__)
        resolved_args = []
        resolved_kwargs = {}
        
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
                
            # Check if we have a value in kwargs
            if param_name in definition.kwargs:
                resolved_kwargs[param_name] = definition.kwargs[param_name]
                continue
                
            # Try to resolve by type annotation
            if param.annotation != param.empty:
                try:
                    resolved_value = await self.resolve(param.annotation)
                    resolved_kwargs[param_name] = resolved_value
                except ValueError:
                    # If required and no default, raise error
                    if param.default == param.empty:
                        raise
                        
        # Create instance
        instance = cls(*resolved_args, **resolved_kwargs)
        
        # Call async init if present
        if hasattr(instance, "__ainit__"):
            await instance.__ainit__()
            
        return instance
        
    def clear_request_scope(self) -> None:
        """Clear request-scoped dependencies"""
        self._request_scope.clear()
        
    def get_all(self, interface: Type[T]) -> List[T]:
        """Get all registered implementations of an interface"""
        definitions = self._definitions.get(interface, [])
        instances = []
        
        for definition in definitions:
            try:
                instance = asyncio.run(self.resolve(interface, definition.name))
                instances.append(instance)
            except Exception as e:
                logger.error(f"Failed to resolve {interface}: {e}")
                
        return instances
        
    def has(self, interface: Type, name: Optional[str] = None) -> bool:
        """Check if a dependency is registered"""
        definitions = self._definitions.get(interface, [])
        
        if not definitions:
            return False
            
        if name:
            return any(d.name == name for d in definitions)
            
        return True
        
    def unregister(self, interface: Type, name: Optional[str] = None) -> bool:
        """Unregister a dependency"""
        if interface not in self._definitions:
            return False
            
        if name:
            before_count = len(self._definitions[interface])
            self._definitions[interface] = [
                d for d in self._definitions[interface]
                if d.name != name
            ]
            removed = before_count > len(self._definitions[interface])
        else:
            removed = bool(self._definitions[interface])
            del self._definitions[interface]
            
        # Remove from singletons if present
        if interface in self._singletons:
            del self._singletons[interface]
            
        return removed
        
    def create_child_container(self) -> 'Container':
        """Create a child container that inherits registrations"""
        child = Container()
        child._definitions = self._definitions.copy()
        # Don't copy singletons - they'll be resolved from parent
        return child


class ServiceProvider:
    """
    Service provider pattern implementation.
    
    Provides a higher-level abstraction over the container.
    """
    
    def __init__(self, container: Optional[Container] = None):
        self.container = container or Container()
        self._services: Dict[str, Any] = {}
        
    def add_service(self, name: str, service: Any) -> None:
        """Add a named service"""
        self._services[name] = service
        self.container.register_instance(type(service), service)
        
    def get_service(self, name: str) -> Any:
        """Get a named service"""
        return self._services.get(name)
        
    async def get_required_service(self, service_type: Type[T]) -> T:
        """Get a required service by type"""
        return await self.container.resolve(service_type)
        
    def configure_services(self, config_func: Callable[[Container], None]) -> None:
        """Configure services using a configuration function"""
        config_func(self.container)
        
    async def create_scope(self) -> 'ServiceScope':
        """Create a new service scope"""
        return ServiceScope(self)
        
        
class ServiceScope:
    """Represents a service scope (e.g., for a request)"""
    
    def __init__(self, provider: ServiceProvider):
        self.provider = provider
        self.container = provider.container
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.container.clear_request_scope()
        
    async def get_service(self, service_type: Type[T]) -> T:
        """Get a service within this scope"""
        return await self.container.resolve(service_type)


# Decorators for dependency injection
def injectable(scope: Scope = Scope.SINGLETON):
    """Decorator to mark a class as injectable"""
    def decorator(cls):
        cls._injectable_scope = scope
        return cls
    return decorator


def inject(container: Container):
    """Decorator to inject dependencies into a function"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            sig = inspect.signature(func)
            injected_kwargs = {}
            
            for param_name, param in sig.parameters.items():
                if param.annotation != param.empty and param_name not in kwargs:
                    try:
                        injected_kwargs[param_name] = await container.resolve(param.annotation)
                    except ValueError:
                        pass  # Skip if not registered
                        
            return await func(*args, **kwargs, **injected_kwargs)
            
        return wrapper
    return decorator