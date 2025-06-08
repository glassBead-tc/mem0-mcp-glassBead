"""
Event Bus System

Provides a publish-subscribe event system for decoupled communication
between components and plugins.
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Set, Union
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
import weakref

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """Priority levels for event handlers"""
    HIGHEST = 0
    HIGH = 25
    NORMAL = 50
    LOW = 75
    LOWEST = 100


@dataclass
class Event:
    """Base event class"""
    name: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.metadata["event_id"] = id(self)


@dataclass
class EventHandler:
    """Wrapper for event handlers"""
    callback: Callable
    priority: EventPriority = EventPriority.NORMAL
    filter: Optional[Callable[[Event], bool]] = None
    once: bool = False
    weak: bool = False
    
    def __post_init__(self):
        if self.weak:
            self.callback = weakref.ref(self.callback)
            
    def matches(self, event: Event) -> bool:
        """Check if handler should process this event"""
        if self.filter:
            return self.filter(event)
        return True
        
    async def invoke(self, event: Event) -> Any:
        """Invoke the handler"""
        callback = self.callback() if self.weak else self.callback
        if callback is None:
            return None
            
        if asyncio.iscoroutinefunction(callback):
            return await callback(event)
        else:
            return callback(event)


class EventBus:
    """
    Central event bus for the system.
    
    Features:
    - Async event handling
    - Event priorities
    - Event filtering
    - Weak references for handlers
    - Event history
    - Event replay
    """
    
    def __init__(self, history_size: int = 1000):
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._history: List[Event] = []
        self._history_size = history_size
        self._middleware: List[Callable] = []
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        
    def subscribe(
        self,
        event_name: str,
        handler: Callable,
        priority: EventPriority = EventPriority.NORMAL,
        filter: Optional[Callable[[Event], bool]] = None,
        once: bool = False,
        weak: bool = False
    ) -> Callable:
        """
        Subscribe to an event.
        
        Args:
            event_name: Name of the event to subscribe to
            handler: Callback function to handle the event
            priority: Priority for handler execution order
            filter: Optional filter function to determine if handler should run
            once: If True, handler will be automatically unsubscribed after first call
            weak: If True, use weak reference to handler
            
        Returns:
            The handler function (for use with unsubscribe)
        """
        if event_name not in self._handlers:
            self._handlers[event_name] = []
            
        event_handler = EventHandler(
            callback=handler,
            priority=priority,
            filter=filter,
            once=once,
            weak=weak
        )
        
        # Insert handler in priority order
        handlers = self._handlers[event_name]
        insert_idx = len(handlers)
        for i, h in enumerate(handlers):
            if h.priority.value > priority.value:
                insert_idx = i
                break
        handlers.insert(insert_idx, event_handler)
        
        logger.debug(f"Subscribed handler to event '{event_name}' with priority {priority.name}")
        return handler
        
    def unsubscribe(self, event_name: str, handler: Callable) -> bool:
        """
        Unsubscribe from an event.
        
        Returns:
            True if handler was found and removed, False otherwise
        """
        if event_name not in self._handlers:
            return False
            
        handlers = self._handlers[event_name]
        for i, h in enumerate(handlers):
            callback = h.callback() if h.weak else h.callback
            if callback == handler:
                handlers.pop(i)
                logger.debug(f"Unsubscribed handler from event '{event_name}'")
                return True
                
        return False
        
    def unsubscribe_all(self, event_name: Optional[str] = None) -> int:
        """
        Unsubscribe all handlers from an event or all events.
        
        Returns:
            Number of handlers removed
        """
        count = 0
        
        if event_name:
            if event_name in self._handlers:
                count = len(self._handlers[event_name])
                del self._handlers[event_name]
        else:
            for handlers in self._handlers.values():
                count += len(handlers)
            self._handlers.clear()
            
        return count
        
    async def emit(
        self,
        event_name: str,
        data: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Emit an event synchronously.
        
        Returns:
            List of results from all handlers
        """
        event = Event(
            name=event_name,
            data=data or {},
            source=source,
            metadata=metadata or {}
        )
        
        # Add to history
        self._add_to_history(event)
        
        # Apply middleware
        for middleware in self._middleware:
            event = await middleware(event)
            if event is None:
                return []  # Event was cancelled
                
        # Get handlers
        handlers = self._handlers.get(event_name, [])
        results = []
        handlers_to_remove = []
        
        # Execute handlers
        for handler in handlers:
            # Check if weak reference is still valid
            if handler.weak and handler.callback() is None:
                handlers_to_remove.append(handler)
                continue
                
            # Check filter
            if not handler.matches(event):
                continue
                
            try:
                result = await handler.invoke(event)
                results.append(result)
                
                # Remove one-time handlers
                if handler.once:
                    handlers_to_remove.append(handler)
                    
            except Exception as e:
                logger.error(f"Error in event handler for '{event_name}': {e}")
                
        # Remove dead/one-time handlers
        for handler in handlers_to_remove:
            self._handlers[event_name].remove(handler)
            
        return results
        
    async def emit_async(
        self,
        event_name: str,
        data: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Emit an event asynchronously (queued for processing).
        """
        event = Event(
            name=event_name,
            data=data or {},
            source=source,
            metadata=metadata or {}
        )
        
        await self._event_queue.put(event)
        
    def add_middleware(self, middleware: Callable[[Event], Event]) -> None:
        """
        Add middleware to process events before handlers.
        
        Middleware can modify or cancel events.
        """
        self._middleware.append(middleware)
        
    def remove_middleware(self, middleware: Callable[[Event], Event]) -> bool:
        """Remove middleware"""
        try:
            self._middleware.remove(middleware)
            return True
        except ValueError:
            return False
            
    def _add_to_history(self, event: Event) -> None:
        """Add event to history"""
        self._history.append(event)
        if len(self._history) > self._history_size:
            self._history.pop(0)
            
    def get_history(
        self,
        event_name: Optional[str] = None,
        limit: Optional[int] = None,
        since: Optional[datetime] = None
    ) -> List[Event]:
        """
        Get event history.
        
        Args:
            event_name: Filter by event name
            limit: Maximum number of events to return
            since: Only return events after this time
        """
        events = self._history
        
        if event_name:
            events = [e for e in events if e.name == event_name]
            
        if since:
            events = [e for e in events if e.timestamp > since]
            
        if limit:
            events = events[-limit:]
            
        return events
        
    async def replay_events(
        self,
        events: List[Event],
        speed: float = 1.0
    ) -> None:
        """
        Replay a list of events.
        
        Args:
            events: Events to replay
            speed: Playback speed multiplier
        """
        if not events:
            return
            
        start_time = events[0].timestamp
        
        for event in events:
            # Calculate delay
            delay = (event.timestamp - start_time).total_seconds() / speed
            if delay > 0:
                await asyncio.sleep(delay)
                
            # Re-emit event
            await self.emit(
                event.name,
                event.data,
                event.source,
                {**event.metadata, "replayed": True}
            )
            
            start_time = event.timestamp
            
    async def start(self) -> None:
        """Start the event bus worker"""
        if self._running:
            return
            
        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        
    async def stop(self) -> None:
        """Stop the event bus worker"""
        self._running = False
        
        if self._worker_task:
            # Send stop signal
            await self._event_queue.put(None)
            await self._worker_task
            self._worker_task = None
            
    async def _worker(self) -> None:
        """Background worker to process queued events"""
        while self._running:
            try:
                event = await self._event_queue.get()
                
                if event is None:  # Stop signal
                    break
                    
                # Process event
                await self.emit(
                    event.name,
                    event.data,
                    event.source,
                    event.metadata
                )
                
            except Exception as e:
                logger.error(f"Error processing queued event: {e}")
                
    def on(self, event_name: str, **kwargs):
        """Decorator for subscribing to events"""
        def decorator(func: Callable) -> Callable:
            self.subscribe(event_name, func, **kwargs)
            return func
        return decorator
        
    def once(self, event_name: str, **kwargs):
        """Decorator for one-time event subscription"""
        def decorator(func: Callable) -> Callable:
            self.subscribe(event_name, func, once=True, **kwargs)
            return func
        return decorator