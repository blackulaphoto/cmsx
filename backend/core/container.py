"""
Dependency injection container for Case Management Suite
"""

from typing import Type, TypeVar, Dict, Any, Callable
from functools import wraps

T = TypeVar('T')

class Container:
    """Simple dependency injection container"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
    
    def register(self, interface: Type[T], implementation: T) -> None:
        """Register a service implementation"""
        self._services[interface.__name__] = implementation
    
    def register_factory(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """Register a factory for creating service instances"""
        self._factories[interface.__name__] = factory
    
    def resolve(self, interface: Type[T]) -> T:
        """Resolve a service instance"""
        if interface.__name__ in self._services:
            return self._services[interface.__name__]
        elif interface.__name__ in self._factories:
            return self._factories[interface.__name__]()
        else:
            raise KeyError(f"Service {interface.__name__} not registered")

# Global container instance
container = Container()

def singleton(interface: Type[T]):
    """Decorator to register a class as a singleton service"""
    def decorator(cls: Type[T]) -> Type[T]:
        instance = cls()
        container.register(interface, instance)
        
        @wraps(cls)
        def wrapper(*args, **kwargs):
            return instance
        
        return wrapper
    return decorator

# Service interfaces
class IAIService:
    """AI service interface"""
    pass

class IRemindersService:
    """Reminders service interface"""
    pass 