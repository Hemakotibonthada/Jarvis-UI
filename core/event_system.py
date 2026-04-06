"""
J.A.R.V.I.S. Event System — Pub/sub event bus for decoupled module communication.
"""

import asyncio
import inspect
from collections import defaultdict
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


@dataclass
class Event:
    """Base event class."""
    name: str
    data: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = ""
    propagate: bool = True  # Set to False to stop propagation


class EventBus:
    """
    Central event bus for decoupled module communication.
    Supports sync and async handlers, priorities, and wildcards.
    """

    def __init__(self):
        self._handlers: dict[str, list[tuple[int, Callable]]] = defaultdict(list)
        self._once_handlers: set[int] = set()
        self._history: list[Event] = []
        self._max_history = 200
        self._middlewares: list[Callable] = []

    def on(self, event_name: str, handler: Callable, priority: int = 0) -> int:
        """
        Register an event handler.
        Higher priority handlers run first.
        Returns handler ID for later removal.
        """
        handler_id = id(handler)
        self._handlers[event_name].append((priority, handler))
        self._handlers[event_name].sort(key=lambda x: -x[0])  # Higher priority first
        return handler_id

    def once(self, event_name: str, handler: Callable, priority: int = 0) -> int:
        """Register a one-time event handler."""
        handler_id = self.on(event_name, handler, priority)
        self._once_handlers.add(id(handler))
        return handler_id

    def off(self, event_name: str, handler: Callable):
        """Remove an event handler."""
        handler_id = id(handler)
        self._handlers[event_name] = [
            (p, h) for p, h in self._handlers[event_name] if id(h) != handler_id
        ]
        self._once_handlers.discard(handler_id)

    def off_all(self, event_name: str = ""):
        """Remove all handlers for an event, or all handlers."""
        if event_name:
            self._handlers[event_name].clear()
        else:
            self._handlers.clear()
            self._once_handlers.clear()

    def use(self, middleware: Callable):
        """Add middleware that processes every event before handlers."""
        self._middlewares.append(middleware)

    async def emit(self, event_name: str, data: dict = None, source: str = "") -> Event:
        """
        Emit an event and call all registered handlers.
        Supports wildcard matching (e.g., 'system.*' matches 'system.startup').
        """
        event = Event(name=event_name, data=data or {}, source=source)

        # Run middlewares
        for middleware in self._middlewares:
            if asyncio.iscoroutinefunction(middleware):
                await middleware(event)
            else:
                middleware(event)
            if not event.propagate:
                return event

        # Record in history
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # Find matching handlers (exact + wildcard)
        handlers_to_call = list(self._handlers.get(event_name, []))

        # Wildcard matching: 'system.*' matches 'system.startup'
        for pattern, handlers in self._handlers.items():
            if pattern.endswith(".*"):
                prefix = pattern[:-2]
                if event_name.startswith(prefix + ".") and pattern != event_name:
                    handlers_to_call.extend(handlers)

        # Global handler '*'
        if "*" in self._handlers:
            handlers_to_call.extend(self._handlers["*"])

        # Sort by priority
        handlers_to_call.sort(key=lambda x: -x[0])

        # Call handlers
        to_remove = []
        for priority, handler in handlers_to_call:
            if not event.propagate:
                break
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                # Don't let handler errors crash the event system
                pass

            # Check if this was a one-time handler
            if id(handler) in self._once_handlers:
                to_remove.append((event_name, handler))
                self._once_handlers.discard(id(handler))

        # Remove one-time handlers
        for ev_name, handler in to_remove:
            self.off(ev_name, handler)

        return event

    def emit_sync(self, event_name: str, data: dict = None, source: str = ""):
        """Synchronous emit for non-async contexts."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.emit(event_name, data, source))
        except RuntimeError:
            # No running loop
            asyncio.run(self.emit(event_name, data, source))

    def get_history(self, event_name: str = "", limit: int = 50) -> list[dict]:
        """Get event history, optionally filtered by name."""
        events = self._history
        if event_name:
            events = [e for e in events if e.name == event_name or e.name.startswith(event_name)]
        return [
            {"name": e.name, "data": e.data, "timestamp": e.timestamp, "source": e.source}
            for e in events[-limit:]
        ]

    def list_events(self) -> dict[str, int]:
        """List all registered event names and handler counts."""
        return {name: len(handlers) for name, handlers in self._handlers.items() if handlers}


# ─── Predefined Event Names ──────────────────────────────────
class Events:
    """Standard event names used across the system."""
    # System lifecycle
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"

    # Voice events
    VOICE_WAKE_WORD = "voice.wake_word"
    VOICE_COMMAND = "voice.command"
    VOICE_SPEAKING_START = "voice.speaking.start"
    VOICE_SPEAKING_END = "voice.speaking.end"

    # Chat events
    CHAT_USER_MESSAGE = "chat.user_message"
    CHAT_ASSISTANT_RESPONSE = "chat.assistant_response"
    CHAT_TOOL_CALL = "chat.tool_call"
    CHAT_TOOL_RESULT = "chat.tool_result"

    # Tool events
    TOOL_REGISTERED = "tool.registered"
    TOOL_EXECUTED = "tool.executed"
    TOOL_ERROR = "tool.error"

    # IoT events
    IOT_SENSOR_UPDATE = "iot.sensor_update"
    IOT_DEVICE_CONNECTED = "iot.device_connected"
    IOT_DEVICE_DISCONNECTED = "iot.device_disconnected"
    IOT_COMMAND_SENT = "iot.command_sent"

    # Client events
    CLIENT_CONNECTED = "client.connected"
    CLIENT_DISCONNECTED = "client.disconnected"

    # Reminder events
    REMINDER_SET = "reminder.set"
    REMINDER_TRIGGERED = "reminder.triggered"

    # File events
    FILE_CREATED = "file.created"
    FILE_DELETED = "file.deleted"

    # Media events
    MEDIA_PLAY = "media.play"
    MEDIA_PAUSE = "media.pause"
    MEDIA_NEXT = "media.next"


# ─── Singleton event bus ──────────────────────────────────────
event_bus = EventBus()
