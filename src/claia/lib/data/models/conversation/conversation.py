"""
Conversation data model.

A pure data model representing a conversation between users and AI assistants,
with support for messages, settings, and an event-based audit trail.

Messages are stored as a directed tree: each Message has a parent_id that
points to the preceding message. Multiple messages may share the same parent_id,
creating branches (used for message editing / versioning).  The currently active
branch is identified by active_head_id — the ID of the leaf message on the active
path. To get the active linear thread, call get_thread().

This is a pure Python object that can exist in memory without file operations.
Persistence is handled by host runtimes (CLI, API, workers) using emitted
domain events and/or direct serialization.
"""

from typing import Dict, Any, Optional, List, Union, Callable
import logging
import json
import time

from ..text import TextArtifact
from ...events import DomainEvent, EventType
from .message import Message
from .conversation_settings import ConversationSettings
from ....enums.conversation import MessageRole


DEFAULT_CONVERSATION_TITLE = "New Conversation"

logger = logging.getLogger(__name__)


class Conversation(TextArtifact):
    """
    Pure data model for conversations.

    Extends TextArtifact to store conversation data as JSON text.
    Persistence is handled externally by host runtimes (CLI, API) via
    domain events and/or direct serialization.

    Domain events serve two purposes:
      1. Audit trail — every mutation is recorded in self.events and serialized.
      2. Runtime notifications — listeners can react to mutations for
         persistence, sync, or other side effects.

    Message tree:
        All messages are stored in the messages list. Each message has a parent_id
        pointing to its predecessor. Multiple messages may share a parent_id,
        creating branches. active_head_id tracks the leaf of the currently active
        branch. get_thread() returns the active linear thread by walking backwards
        from active_head_id.
    """

    @staticmethod
    def _format_prompt(prompt: Optional[Union[str, Dict[str, str]]]) -> Dict[str, str]:
        if prompt is None:
            return {"system": ""}
        elif isinstance(prompt, str):
            return {"system": prompt}
        elif isinstance(prompt, dict):
            return prompt
        else:
            return {"system": str(prompt)}

    def __init__(self,
                 id: Optional[str] = None,
                 title: str = DEFAULT_CONVERSATION_TITLE,
                 prompt: Optional[Union[str, Dict[str, str]]] = None,
                 messages: Optional[List[Union[Message, Dict[str, Any]]]] = None,
                 events: Optional[List[Union[DomainEvent, Dict[str, Any]]]] = None,
                 settings: Optional[Union[ConversationSettings, Dict[str, Any]]] = None,
                 active_head_id: Optional[str] = None,
                 created_at: Optional[float] = None,
                 updated_at: Optional[float] = None,
                 **kwargs):
        super().__init__(
            name=kwargs.pop('name', f"conversation-{id or 'new'}"),
            id=id,
            media_type='application/json',
            encoding='utf-8',
            created_at=created_at,
            updated_at=updated_at,
            **kwargs
        )

        self.title = title
        self.prompt = self._format_prompt(prompt)
        self.metadata['title'] = title

        self.messages: List[Message] = []
        if messages:
            for m in messages:
                self.messages.append(m if isinstance(m, Message) else Message.from_dict(m))

        if active_head_id:
            self.active_head_id: Optional[str] = active_head_id
        elif self.messages:
            self.active_head_id = self.messages[-1].message_id
        else:
            self.active_head_id = None

        # Persisted audit trail
        self.events: List[DomainEvent] = []
        if events:
            for e in events:
                self.events.append(e if isinstance(e, DomainEvent) else DomainEvent.from_dict(e))

        if settings is None:
            self.settings = ConversationSettings()
        elif isinstance(settings, ConversationSettings):
            self.settings = settings
        else:
            self.settings = ConversationSettings.from_dict(settings)

        # Transient runtime queue (not serialized) + listeners
        self._pending_events: List[DomainEvent] = []
        self._event_listeners: List[Callable[[DomainEvent], None]] = []

        if not self.events:
            self.emit_event(EventType.CONVERSATION_CREATED, {
                "title": self.title,
                "system_prompt": self.prompt.get("system", ""),
            })

    # ---------------------------------------------------------------------- #
    # Domain events                                                            #
    # ---------------------------------------------------------------------- #

    def emit_event(self, event_type: EventType,
                   metadata: Optional[Dict[str, Any]] = None,
                   entity_id: Optional[str] = None,
                   parent_id: Optional[str] = None) -> DomainEvent:
        """Record a domain event in the audit trail and notify listeners."""
        event = DomainEvent(
            event_type=event_type,
            entity_id=entity_id or self.id,
            parent_id=parent_id,
            metadata=metadata or {},
        )
        self.events.append(event)
        self._pending_events.append(event)
        for listener in list(self._event_listeners):
            try:
                listener(event)
            except Exception as e:
                logger.warning(f"Event listener failed: {e}")
        return event

    def add_event_listener(self, listener: Callable[[DomainEvent], None]) -> None:
        if listener not in self._event_listeners:
            self._event_listeners.append(listener)

    def remove_event_listener(self, listener: Callable[[DomainEvent], None]) -> None:
        if listener in self._event_listeners:
            self._event_listeners.remove(listener)

    def peek_events(self) -> List[DomainEvent]:
        """Return pending events without clearing."""
        return list(self._pending_events)

    def pull_events(self) -> List[DomainEvent]:
        """Return and clear pending events (recommended runtime API)."""
        events = list(self._pending_events)
        self._pending_events.clear()
        return events

    def clear_pending_events(self) -> None:
        self._pending_events.clear()

    # ---------------------------------------------------------------------- #
    # Serialization                                                             #
    # ---------------------------------------------------------------------- #

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "title": self.title,
            "prompt": self.prompt,
            "messages": [m.to_dict() for m in self.messages],
            "active_head_id": self.active_head_id,
            "events": [e.to_dict() for e in self.events],
            "settings": self.settings.to_dict(),
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
        return cls(
            id=data.get("id"),
            title=data.get("title", DEFAULT_CONVERSATION_TITLE),
            prompt=data.get("prompt"),
            messages=data.get("messages", []),
            events=data.get("events", []),
            settings=data.get("settings"),
            active_head_id=data.get("active_head_id"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            name=data.get("name"),
            is_reference=data.get("is_reference", False),
            source_uri=data.get("source_uri"),
            metadata=data.get("metadata", {}),
        )

    def load_content(self) -> str:
        if self._content_loaded and self._content is not None:
            return self._content
        return self.content

    @property
    def content(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def set_content(self, content: str) -> None:
        data = json.loads(content)

        self.title = data.get("title", self.title)
        self.prompt = self._format_prompt(data.get("prompt", self.prompt))

        self.messages = []
        for m in data.get("messages", []):
            self.messages.append(m if isinstance(m, Message) else Message.from_dict(m))

        self.active_head_id = data.get("active_head_id")
        if not self.active_head_id and self.messages:
            self.active_head_id = self.messages[-1].message_id

        self.events = []
        for e in data.get("events", []):
            self.events.append(e if isinstance(e, DomainEvent) else DomainEvent.from_dict(e))

        settings_data = data.get("settings")
        if settings_data:
            if isinstance(settings_data, ConversationSettings):
                self.settings = settings_data
            else:
                self.settings = ConversationSettings.from_dict(settings_data)

        self._content = content
        self._content_loaded = True
        self.size = len(content.encode(self.encoding))
        self.updated_at = time.time()

    # ---------------------------------------------------------------------- #
    # Tree traversal                                                           #
    # ---------------------------------------------------------------------- #

    def _build_id_map(self) -> Dict[str, Message]:
        return {m.message_id: m for m in self.messages}

    def get_thread(self, head_id: Optional[str] = None) -> List[Message]:
        """Return ordered messages from root to head_id (chronological)."""
        target = head_id or self.active_head_id
        if not target or not self.messages:
            return []

        by_id = self._build_id_map()
        chain: List[Message] = []
        current_id: Optional[str] = target
        seen = set()

        while current_id is not None:
            if current_id in seen:
                logger.warning(f"Cycle detected in message chain at {current_id}")
                break
            msg = by_id.get(current_id)
            if msg is None:
                break
            seen.add(current_id)
            chain.append(msg)
            current_id = msg.parent_id

        chain.reverse()
        return chain

    def get_siblings(self, message_id: str) -> List[Message]:
        """Return all messages sharing the same parent_id, ordered by created_at."""
        by_id = self._build_id_map()
        target = by_id.get(message_id)
        if not target:
            return []
        siblings = [m for m in self.messages if m.parent_id == target.parent_id]
        siblings.sort(key=lambda m: m.created_at)
        return siblings

    def get_branch_head(self, message_id: str) -> Optional[str]:
        """Find the most recently created leaf reachable from message_id."""
        children_map: Dict[str, List[Message]] = {}
        for m in self.messages:
            if m.parent_id:
                children_map.setdefault(m.parent_id, []).append(m)

        by_id = self._build_id_map()
        if message_id not in by_id:
            return None

        leaves: List[str] = []

        def dfs(mid: str) -> None:
            kids = children_map.get(mid, [])
            if not kids:
                leaves.append(mid)
            else:
                for child in kids:
                    dfs(child.message_id)

        dfs(message_id)
        if not leaves:
            return message_id
        leaves.sort(key=lambda lid: by_id[lid].created_at if lid in by_id else 0, reverse=True)
        return leaves[0]

    # ---------------------------------------------------------------------- #
    # Message management                                                       #
    # ---------------------------------------------------------------------- #

    def add_message(self,
                    speaker: Union[MessageRole, str],
                    content: str,
                    file_ids: Optional[List[str]] = None,
                    parent_id: Optional[str] = None) -> Message:
        """Add a message to the conversation tree."""
        effective_parent_id = parent_id if parent_id is not None else self.active_head_id

        message = Message(
            speaker=speaker,
            content=content,
            file_ids=file_ids or [],
            parent_id=effective_parent_id,
        )
        message.extract_inline_args()

        self.messages.append(message)
        self.active_head_id = message.message_id
        self.updated_at = time.time()

        meta = {
            "message_id": message.message_id,
            "parent_id": message.parent_id,
            "speaker": message.speaker.value,
            "content_preview": message.content[:50] + ("..." if len(message.content) > 50 else ""),
        }
        if message.has_inline_args():
            meta["inline_args_count"] = len(message.inline_args)

        self.emit_event(EventType.MESSAGE_CREATED, meta,
                        entity_id=message.message_id, parent_id=message.parent_id)
        return message

    def update_message(self, message_id: str, content: Optional[str] = None,
                       file_ids: Optional[List[str]] = None) -> Optional[Message]:
        """Update a message in-place (content fix, not a branch)."""
        for message in self.messages:
            if message.message_id == message_id:
                if content is not None:
                    message.content = content
                    message.inline_args = {}
                    message.extract_inline_args()
                if file_ids is not None:
                    message.file_ids = file_ids

                message.updated_at = time.time()
                self.updated_at = time.time()

                meta = {
                    "message_id": message_id,
                    "content_preview": message.content[:50] + ("..." if len(message.content) > 50 else ""),
                }
                if message.has_inline_args():
                    meta["inline_args_count"] = len(message.inline_args)

                self.emit_event(EventType.MESSAGE_UPDATED, meta,
                                entity_id=message.message_id, parent_id=message.parent_id)
                return message

        logger.error(f"Message not found for update: {message_id}")
        return None

    def delete_message(self, message_id: str) -> bool:
        """Delete a message from the conversation tree."""
        for i, message in enumerate(self.messages):
            if message.message_id == message_id:
                deleted = self.messages.pop(i)
                self.updated_at = time.time()
                if self.active_head_id == message_id:
                    self.active_head_id = deleted.parent_id

                self.emit_event(EventType.MESSAGE_DELETED, {
                    "message_id": message_id,
                    "speaker": deleted.speaker.value,
                }, entity_id=message_id, parent_id=deleted.parent_id)
                return True

        logger.error(f"Message not found for deletion: {message_id}")
        return False

    def get_message(self, message_id: str) -> Optional[Message]:
        for message in self.messages:
            if message.message_id == message_id:
                return message
        return None

    def get_latest_message(self) -> Optional[Message]:
        if self.active_head_id:
            msg = self.get_message(self.active_head_id)
            if msg:
                return msg
        thread = self.get_thread()
        return thread[-1] if thread else None

    def get_messages(self, speaker: Optional[Union[MessageRole, List[MessageRole]]] = None) -> List[Message]:
        thread = self.get_thread()
        if speaker is None:
            return thread
        speakers = [speaker] if not isinstance(speaker, list) else speaker
        speakers = [s if isinstance(s, MessageRole) else MessageRole(s) for s in speakers]
        return [m for m in thread if m.speaker in speakers]

    def stream_message(self, message_id: str, content: str, append: bool = False,
                       end: bool = False) -> Optional[Message]:
        """Update a message's content for streaming.

        Emits MESSAGE_STREAM_START on the first call per message, and
        MESSAGE_STREAM_END when end=True.  Intermediate chunks are silent
        to avoid flooding the audit trail.
        """
        for message in self.messages:
            if message.message_id == message_id:
                if append:
                    message.safe_append_content(content)
                else:
                    message.safe_update_content(content)
                self.updated_at = time.time()

                has_start = any(
                    e.event_type == EventType.MESSAGE_STREAM_START and
                    e.metadata.get("message_id") == message_id
                    for e in self.events
                )
                if not has_start:
                    self.emit_event(EventType.MESSAGE_STREAM_START, {
                        "message_id": message_id,
                        "speaker": message.speaker.value,
                    }, entity_id=message_id, parent_id=message.parent_id)

                if end:
                    self.emit_event(EventType.MESSAGE_STREAM_END, {
                        "message_id": message_id,
                        "speaker": message.speaker.value,
                        "content_preview": message.content[:50] + ("..." if len(message.content) > 50 else ""),
                    }, entity_id=message_id, parent_id=message.parent_id)

                return message

        logger.error(f"Message not found for streaming update: {message_id}")
        return None

    # ---------------------------------------------------------------------- #
    # File attachment methods                                                  #
    # ---------------------------------------------------------------------- #

    def attach_file(self, message_id: str, file_id: str) -> bool:
        message = self.get_message(message_id)
        if not message:
            logger.error(f"Cannot attach file: message not found: {message_id}")
            return False
        if file_id in message.file_ids:
            return True

        message.file_ids.append(file_id)
        message.updated_at = time.time()
        self.updated_at = time.time()

        self.emit_event(EventType.ATTACHMENT_ADDED,
                        {"message_id": message_id, "file_id": file_id},
                        entity_id=message_id, parent_id=message.parent_id)
        return True

    def detach_file(self, message_id: str, file_id: str) -> bool:
        message = self.get_message(message_id)
        if not message:
            logger.error(f"Cannot detach file: message not found: {message_id}")
            return False
        if file_id not in message.file_ids:
            return False

        message.file_ids.remove(file_id)
        message.updated_at = time.time()
        self.updated_at = time.time()

        self.emit_event(EventType.ATTACHMENT_REMOVED,
                        {"message_id": message_id, "file_id": file_id},
                        entity_id=message_id, parent_id=message.parent_id)
        return True

    # ---------------------------------------------------------------------- #
    # Prompt and settings management                                           #
    # ---------------------------------------------------------------------- #

    def get_system_prompt(self, **kwargs) -> Optional[str]:
        system_prompt = self.prompt.get("system", "")
        if not system_prompt or not system_prompt.strip():
            return None
        return self.apply_substitutions(system_prompt, **kwargs)

    def apply_substitutions(self, text: str, **kwargs) -> str:
        if kwargs and any(f"{{{key}}}" in text for key in kwargs):
            try:
                text = text.format(**kwargs)
            except KeyError as e:
                logger.warning(f"Missing key in text substitution: {e}")
            except Exception as e:
                logger.error(f"Error during text substitution: {e}")
        return text

    def change_title(self, new_title: str) -> None:
        old_title = self.title
        self.title = new_title
        self.metadata['title'] = new_title
        self.updated_at = time.time()
        self.emit_event(EventType.TITLE_CHANGED,
                        {"old_title": old_title, "new_title": new_title})

    def change_prompt(self, new_prompt: Union[str, Dict[str, str]]) -> None:
        old_prompt = self.prompt.get("system", "")
        self.prompt = self._format_prompt(new_prompt)
        self.updated_at = time.time()
        self.emit_event(EventType.PROMPT_CHANGED, {
            "old_prompt": old_prompt,
            "new_prompt": self.prompt.get("system", ""),
        })

    def update_settings(self, settings: ConversationSettings) -> None:
        changes = {}
        if settings.streaming != self.settings.streaming:
            self.settings.streaming = settings.streaming
            changes["streaming"] = settings.streaming

        for key, value in settings.text_settings.items():
            if self.settings.text_settings.get(key) != value:
                self.settings.text_settings[key] = value
                changes.setdefault("text_settings", {})[key] = value

        for key, value in settings.image_settings.items():
            if self.settings.image_settings.get(key) != value:
                self.settings.image_settings[key] = value
                changes.setdefault("image_settings", {})[key] = value

        if changes:
            self.updated_at = time.time()
            self.emit_event(EventType.SETTINGS_UPDATED, changes)

    def get_settings(self) -> ConversationSettings:
        return self.settings

    # ---------------------------------------------------------------------- #
    # File management convenience methods                                      #
    # ---------------------------------------------------------------------- #

    def load_message_files(self, message_id: str, file_repo, load_content: bool = False) -> List:
        message = self.get_message(message_id)
        if not message or not message.file_ids:
            return []
        return file_repo.load_multiple(message.file_ids, load_content=load_content)

    def load_all_files(self, file_repo, load_content: bool = False) -> Dict[str, List]:
        result = {}
        for message in self.get_thread():
            if message.file_ids:
                files = file_repo.load_multiple(message.file_ids, load_content=load_content)
                if files:
                    result[message.message_id] = files
        return result

    def get_all_file_ids(self) -> List[str]:
        file_ids = set()
        for message in self.messages:
            file_ids.update(message.file_ids)
        return list(file_ids)
