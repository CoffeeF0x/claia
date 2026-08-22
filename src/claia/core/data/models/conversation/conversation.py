"""
Conversation data model.

A pure data model representing a conversation between users and AI
assistants, with support for messages and an event-based audit trail.

Messages are stored as a directed tree: each Message has a parent_id
that points to the preceding message. Multiple messages may share the
same parent_id, creating branches (used for message editing /
versioning). The currently active branch is identified by
active_head_id — the ID of the leaf message on the active path. To get
the active linear thread, call get_thread().

Conversation is a pure data carrier. Generation parameters (temperature,
max_tokens, streaming, etc.) do not live on the Conversation; they are
declared by architectures/models via ``ParamSpec`` (see
``claia.core.plugins.base``) and supplied per-call via
``Process.parameters`` or ``Registry.run`` kwargs.

This is a pure Python object that can exist in memory without file
operations. Persistence is handled by host runtimes (CLI, API, workers)
using emitted domain events and/or direct serialization.
"""

from typing import Dict, Any, Optional, List, Union, Callable
import logging
import time
import uuid

from ...events import DomainEvent, EventType
from .message import Message
from ....enums.conversation import MessageRole
from ....parser.types import TagType


DEFAULT_CONVERSATION_TITLE = "New Conversation"

logger = logging.getLogger(__name__)

# Type alias for the observer callback. Receives the domain event and the
# message it relates to (or None for conversation-level events).
EventCallback = Callable[[DomainEvent, Optional["Message"]], None]


class Conversation:
    """
    Pure data model for conversations.

    Conversation-domain type that may reference artifacts; it is not
    an artifact itself. Persistence is host-owned (CLI JsonStore,
    Slate DB, …) via domain events and/or direct serialization.

    Domain events serve two purposes:
      1. Audit trail — every mutation is recorded in self.events and serialized.
      2. Runtime notifications — a single observer callback (set via the
         ``on_event`` constructor argument or :meth:`observe`) is invoked for
         every domain event so integrators can persist or sync mutations as
         they happen.

    Observer contract (event_type -> message argument passed to the callback):

      ====================== ==========================================
      Event                  message argument
      ====================== ==========================================
      MESSAGE_CREATED        the new message
      MESSAGE_UPDATED        post-mutation state of the message
      MESSAGE_DELETED        state of the message just before deletion
      MESSAGE_STREAM_START   the empty message being streamed into
      MESSAGE_STREAM_END     final state of the streamed message
      ATTACHMENT_ADDED       the message the attachment was added to
      ATTACHMENT_REMOVED     the message the attachment was removed from
      CONVERSATION_CREATED   None (conversation-level)
      TITLE_CHANGED          None
      ====================== ==========================================

    Streaming mutations -- :meth:`append_stream_chunk` -- intentionally do not
    fire the observer or emit events. Per-chunk notifications would flood the
    audit trail and the callback. Applications that need to persist streamed
    content as it arrives should call :meth:`append_stream_chunk` for the
    in-memory update and flush content to durable storage on their own
    cadence (e.g. every N characters or every M milliseconds).

    Observer exceptions are caught and logged so a misbehaving observer
    cannot corrupt conversation state. Observers are expected to handle
    their own errors.

    :meth:`pull_events` remains available as an alternative pull-based API
    for integrators that prefer to drain pending events at request boundaries
    instead of reacting in real time. Use one pattern or the other -- not
    both -- for a given conversation.

    Message tree:
        All messages are stored in the messages list. Each message has a parent_id
        pointing to its predecessor. Multiple messages may share a parent_id,
        creating branches. active_head_id tracks the leaf of the currently active
        branch. get_thread() returns the active linear thread by walking backwards
        from active_head_id.
    """

    def __init__(self,
                 id: Optional[str] = None,
                 title: str = DEFAULT_CONVERSATION_TITLE,
                 messages: Optional[List[Union[Message, Dict[str, Any]]]] = None,
                 events: Optional[List[Union[DomainEvent, Dict[str, Any]]]] = None,
                 active_head_id: Optional[str] = None,
                 created_at: Optional[float] = None,
                 updated_at: Optional[float] = None,
                 on_event: Optional[EventCallback] = None,
                 name: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 **kwargs):
        del kwargs  # accept and ignore unused constructor kwargs
        self.id = id or str(uuid.uuid4())
        self.name = name or f"conversation-{self.id}"
        self.title = title
        self.metadata: Dict[str, Any] = metadata or {}
        self.created_at = created_at or time.time()
        self.updated_at = updated_at or self.created_at

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
                if isinstance(e, DomainEvent):
                    self.events.append(e)
                    continue
                try:
                    self.events.append(DomainEvent.from_dict(e))
                except KeyError:
                    continue

        # Transient runtime queue (not serialized) + single observer.
        self._pending_events: List[DomainEvent] = []
        self._on_event: Optional[EventCallback] = on_event

        if not self.events:
            self._record(
                EventType.CONVERSATION_CREATED,
                None,
                {"title": self.title},
            )

    # ---------------------------------------------------------------------- #
    # Domain events                                                            #
    # ---------------------------------------------------------------------- #

    def _record(self,
                event_type: EventType,
                message: Optional[Message],
                metadata: Optional[Dict[str, Any]] = None,
                entity_id: Optional[str] = None,
                parent_id: Optional[str] = None) -> DomainEvent:
        """
        Internal: record a domain event and notify the observer.

        Centralizes event creation so every mutation goes through the same
        path: append to the audit trail, append to the transient pending
        queue, and invoke the observer callback (if any) with the event and
        the related message.
        """
        event = DomainEvent(
            event_type=event_type,
            entity_id=entity_id or (message.message_id if message else self.id),
            parent_id=parent_id,
            metadata=metadata or {},
        )
        self.events.append(event)
        self._pending_events.append(event)
        if self._on_event is not None:
            try:
                self._on_event(event, message)
            except Exception as e:
                logger.warning(f"Event observer failed: {e}")
        return event

    def emit_event(self, event_type: EventType,
                   metadata: Optional[Dict[str, Any]] = None,
                   entity_id: Optional[str] = None,
                   parent_id: Optional[str] = None) -> DomainEvent:
        """
        Record a domain event in the audit trail and notify the observer.

        Public escape hatch for emitting events that aren't covered by the
        built-in mutation methods. Most callers should use the dedicated
        mutation methods (add_message, update_message, ...) instead.
        """
        return self._record(event_type, None, metadata, entity_id, parent_id)

    def observe(self, on_event: Optional[EventCallback]) -> None:
        """
        Set (or clear) the single observer callback.

        Pass ``None`` to remove the current observer. The callback is invoked
        for every domain event with ``(event, message)`` where ``message`` is
        the related Message (or ``None`` for conversation-level events). See
        the class docstring for the full event-to-message contract.
        """
        self._on_event = on_event

    def peek_events(self) -> List[DomainEvent]:
        """Return pending events without clearing."""
        return list(self._pending_events)

    def pull_events(self) -> List[DomainEvent]:
        """
        Return and clear pending events.

        Pull-based alternative to the observer callback for integrators that
        prefer to drain events at request boundaries. Use one pattern or the
        other -- not both -- for a given conversation.
        """
        events = list(self._pending_events)
        self._pending_events.clear()
        return events

    def clear_pending_events(self) -> None:
        self._pending_events.clear()

    # ---------------------------------------------------------------------- #
    # Serialization                                                             #
    # ---------------------------------------------------------------------- #

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "title": self.title,
            "messages": [m.to_dict() for m in self.messages],
            "active_head_id": self.active_head_id,
            "events": [e.to_dict() for e in self.events],
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
        return cls(
            id=data.get("id"),
            title=data.get("title", DEFAULT_CONVERSATION_TITLE),
            messages=data.get("messages", []),
            events=data.get("events", []),
            active_head_id=data.get("active_head_id"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            name=data.get("name"),
            metadata=data.get("metadata", {}),
        )

    # ---------------------------------------------------------------------- #
    # Model-ready sequence                                                     #
    # ---------------------------------------------------------------------- #

    def export_thread(self, include_utility: bool = False) -> List[Message]:
        """Return the active message view (structural, not model-ready)."""
        return self.get_thread(include_utility=include_utility)

    def to_message_sequence(
        self,
        supported_artifact_types,
        sequence_cls=None,
        include_utility: bool = False,
        system: Optional[str] = None,
    ):
        """Build a filtered message sequence for a model.

        Copies each active-thread message, keeps only artifacts whose
        ``ArtifactType`` is in ``supported_artifact_types``, drops turns
        that end up empty, and returns an instance of ``sequence_cls``
        (default ``MessageSequence``).
        """
        from ....enums.data import ArtifactType
        from .message_sequence import MessageSequence

        if sequence_cls is None:
            sequence_cls = MessageSequence

        allowed = set(supported_artifact_types or [])
        copies = []
        for message in self.export_thread(include_utility=include_utility):
            filtered = [
                a for a in (message.artifacts or [])
                if ArtifactType.from_artifact(a) in allowed
            ]
            if not filtered:
                continue
            copies.append(message.copy_with_artifacts(filtered))

        if system is not None:
            system = system.strip() or None
        return sequence_cls(messages=copies, system=system)

    def to_model_inputs(
        self,
        definition=None,
        system: Optional[str] = None,
        include_utility: bool = False,
    ):
        """Translate this conversation into model inputs.

        Sequence models get a filtered ``MessageSequence`` (optional
        ``system`` becomes a ``SYSTEM`` turn). Other models get supported
        artifacts from the latest thread message.
        """
        from ....definitions.model_definition import ModelDefinition
        from ....enums.data import ArtifactType

        definition = definition or ModelDefinition()
        artifact_types = definition.artifact_types() or [ArtifactType.TEXT]
        sequence_cls = definition.sequence_class()
        if sequence_cls is not None:
            return self.to_message_sequence(
                supported_artifact_types=artifact_types,
                sequence_cls=sequence_cls,
                include_utility=include_utility,
                system=system,
            )

        thread = self.export_thread(include_utility=include_utility)
        if not thread:
            return []
        allowed = set(artifact_types)
        return [
            artifact
            for artifact in (thread[-1].artifacts or [])
            if ArtifactType.from_artifact(artifact) in allowed
        ]

    # ---------------------------------------------------------------------- #
    # Tree traversal                                                           #
    # ---------------------------------------------------------------------- #

    def _build_id_map(self) -> Dict[str, Message]:
        return {m.message_id: m for m in self.messages}

    def get_thread(self,
                   head_id: Optional[str] = None,
                   include_utility: bool = False) -> List[Message]:
        """Return ordered messages from root to head_id (chronological).

        Args:
            head_id: Optional starting leaf. Defaults to
                ``active_head_id``.
            include_utility: If ``False`` (the default) messages with
                ``role == MessageRole.UTILITY`` are filtered out of the
                returned thread. Utility messages are derived siblings
                of an assistant message — parsed tag spans that
                consumers like the model-facing prompt builder should
                not echo back. Pass ``True`` to include them (e.g., for
                UI rendering, debugging, or replay). See the ExoFox
                docs repo ``claia/reference/conversation.md`` Decisions.
        """
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
        if not include_utility:
            chain = [m for m in chain if m.speaker != MessageRole.UTILITY]
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
                    content: str = "",
                    artifacts: Optional[List[Any]] = None,
                    parent_id: Optional[str] = None) -> Message:
        """Add a message to the conversation tree."""
        effective_parent_id = parent_id if parent_id is not None else self.active_head_id

        message = Message(
            speaker=speaker,
            content=content,
            artifacts=artifacts,
            parent_id=effective_parent_id,
        )

        self.messages.append(message)
        self.active_head_id = message.message_id
        self.updated_at = time.time()

        meta = {
            "message_id": message.message_id,
            "parent_id": message.parent_id,
            "speaker": message.speaker.value,
            "content_preview": message.content[:50] + ("..." if len(message.content) > 50 else ""),
        }

        self._record(EventType.MESSAGE_CREATED, message, meta,
                     entity_id=message.message_id, parent_id=message.parent_id)
        return message

    def append_utility(self,
                       tag_type: TagType,
                       content: str,
                       source_message_id: str,
                       start_index: Optional[int] = None,
                       end_index: Optional[int] = None,
                       attributes: Optional[Dict[str, str]] = None,
                       parent_id: Optional[str] = None) -> Message:
        """Append a ``UTILITY``-role sibling message derived from a tag.

        Parsed tag spans (tool calls, thinking blocks, references, …)
        become their own first-class messages that reference a source
        assistant message by id. This helper is the data-model entry
        point for creating one.

        Behaviour:

        - ``parent_id`` defaults to the current ``active_head_id`` so
          successive utilities and follow-up user/assistant turns
          chain chronologically through the tree. Pass an explicit
          ``parent_id`` to anchor elsewhere (e.g. directly to the
          source assistant message when several utilities were parsed
          out of order).
        - ``source_message_id`` is the explicit, immutable link to
          the assistant message the tag came from. It is **not**
          required to equal ``parent_id`` and remains stable across
          subsequent edits to the tree.
        - ``active_head_id`` advances to the new utility message so
          later additions follow it. Default ``get_thread()`` calls
          filter utility messages out, so the linearization seen by
          models is unaffected.
        - The standard ``MESSAGE_CREATED`` domain event is emitted,
          carrying ``tag_type`` / ``source_message_id`` in the
          event metadata for persistence/observer consumers.

        Args:
            tag_type: Categorical kind of the parsed tag.
            content: Raw content between the open and close tokens.
            source_message_id: ``message_id`` of the source assistant
                message the utility was parsed from.
            start_index: Absolute character offset of the open token
                in the source assistant message text.
            end_index: Exclusive end offset just past the close
                token in the source assistant message text.
            attributes: Parsed XML-style attributes from the open
                token, or ``None`` for tags without attributes.
            parent_id: Optional override for the tree parent;
                defaults to ``active_head_id``.
        """
        effective_parent_id = parent_id if parent_id is not None else self.active_head_id

        message = Message(
            speaker=MessageRole.UTILITY,
            content=content,
            parent_id=effective_parent_id,
            tag_type=tag_type,
            source_message_id=source_message_id,
            start_index=start_index,
            end_index=end_index,
            attributes=attributes,
        )

        self.messages.append(message)
        self.active_head_id = message.message_id
        self.updated_at = time.time()

        meta: Dict[str, Any] = {
            "message_id": message.message_id,
            "parent_id": message.parent_id,
            "speaker": message.speaker.value,
            "tag_type": tag_type.value,
            "source_message_id": source_message_id,
        }
        if start_index is not None:
            meta["start_index"] = start_index
        if end_index is not None:
            meta["end_index"] = end_index
        if message.attributes:
            meta["attribute_count"] = len(message.attributes)

        self._record(EventType.MESSAGE_CREATED, message, meta,
                     entity_id=message.message_id, parent_id=message.parent_id)
        return message

    def update_message(self, message_id: str, content: Optional[str] = None,
                       artifacts: Optional[List[Any]] = None) -> Optional[Message]:
        """Update a message in-place (content fix, not a branch)."""
        for message in self.messages:
            if message.message_id == message_id:
                if content is not None:
                    message.content = content
                if artifacts is not None:
                    message.artifacts = list(artifacts)

                message.updated_at = time.time()
                self.updated_at = time.time()

                meta = {
                    "message_id": message_id,
                    "content_preview": message.content[:50] + ("..." if len(message.content) > 50 else ""),
                }

                self._record(EventType.MESSAGE_UPDATED, message, meta,
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

                self._record(EventType.MESSAGE_DELETED, deleted, {
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

    def get_messages(self,
                     speaker: Optional[Union[MessageRole, List[MessageRole]]] = None,
                     include_utility: bool = False) -> List[Message]:
        """Return active-thread messages, optionally filtered by speaker.

        ``include_utility`` mirrors :meth:`get_thread`: utility messages
        are excluded by default. Explicitly requesting a speaker that
        includes ``MessageRole.UTILITY`` also returns utility messages
        regardless of ``include_utility``, since the caller has asked
        for that role specifically.
        """
        speakers: Optional[List[MessageRole]] = None
        if speaker is not None:
            raw = [speaker] if not isinstance(speaker, list) else speaker
            speakers = [s if isinstance(s, MessageRole) else MessageRole(s) for s in raw]

        # If the caller explicitly asks for utility messages by speaker,
        # surface them even when ``include_utility`` is False.
        wants_utility = bool(speakers and MessageRole.UTILITY in speakers)
        thread = self.get_thread(include_utility=include_utility or wants_utility)

        if speakers is None:
            return thread
        return [m for m in thread if m.speaker in speakers]

    def start_streaming_message(self,
                                speaker: Union[MessageRole, str],
                                parent_id: Optional[str] = None) -> Message:
        """
        Create an empty message that subsequent ``append_stream_chunk`` calls
        will fill in, and emit MESSAGE_STREAM_START.

        The message is appended to the tree with the resolved parent_id and
        becomes the active head. The observer is invoked once with the
        empty message so integrators can persist a placeholder row before
        any tokens arrive.
        """
        effective_parent_id = parent_id if parent_id is not None else self.active_head_id

        message = Message(
            speaker=speaker,
            content="",
            parent_id=effective_parent_id,
        )

        self.messages.append(message)
        self.active_head_id = message.message_id
        self.updated_at = time.time()

        self._record(EventType.MESSAGE_STREAM_START, message, {
            "message_id": message.message_id,
            "speaker": message.speaker.value,
            "parent_id": message.parent_id,
        }, entity_id=message.message_id, parent_id=message.parent_id)

        return message

    def append_stream_chunk(self, message_id: str, chunk: str) -> Optional[Message]:
        """
        Append a chunk to a streaming message's content. Silent: this method
        does not emit a domain event or invoke the observer.

        Per-chunk notifications would flood the event log and the observer.
        Applications that need to persist streamed content as it arrives
        should flush content on their own cadence (every N characters or
        every M milliseconds) outside of the observer pipeline.
        """
        for message in self.messages:
            if message.message_id == message_id:
                message.safe_append_content(chunk)
                self.updated_at = time.time()
                return message

        logger.error(f"Message not found for stream chunk: {message_id}")
        return None

    def end_streaming_message(self, message_id: str,
                              error: Optional[str] = None) -> Optional[Message]:
        """
        Emit MESSAGE_STREAM_END for an in-progress streaming message.

        Pass ``error`` (a short string) when the stream terminated abnormally;
        the value is included in the event metadata so persistence layers can
        record that the partial content reflects a failed run.
        """
        for message in self.messages:
            if message.message_id == message_id:
                self.updated_at = time.time()
                meta: Dict[str, Any] = {
                    "message_id": message_id,
                    "speaker": message.speaker.value,
                    "content_preview": message.content[:50] + ("..." if len(message.content) > 50 else ""),
                }
                if error is not None:
                    meta["error"] = error

                self._record(EventType.MESSAGE_STREAM_END, message, meta,
                             entity_id=message_id, parent_id=message.parent_id)
                return message

        logger.error(f"Message not found for stream end: {message_id}")
        return None

    # ---------------------------------------------------------------------- #
    # Artifact attachment                                                      #
    # ---------------------------------------------------------------------- #

    def attach_artifact(self, message_id: str, artifact) -> bool:
        """Attach an artifact (File, Link, Image, …) to a message."""
        message = self.get_message(message_id)
        if not message:
            logger.error(f"Cannot attach artifact: message not found: {message_id}")
            return False

        message.add_artifact(artifact)
        self.updated_at = time.time()

        self._record(EventType.ATTACHMENT_ADDED, message,
                     {"message_id": message_id, "artifact_id": getattr(artifact, "id", None)},
                     entity_id=message_id, parent_id=message.parent_id)
        return True

    def detach_artifact(self, message_id: str, artifact_id: str) -> bool:
        """Remove an artifact from a message by id."""
        message = self.get_message(message_id)
        if not message:
            logger.error(f"Cannot detach artifact: message not found: {message_id}")
            return False

        before = len(message.artifacts)
        message.artifacts = [a for a in message.artifacts if a.id != artifact_id]
        if len(message.artifacts) == before:
            return False

        message.updated_at = time.time()
        self.updated_at = time.time()

        self._record(EventType.ATTACHMENT_REMOVED, message,
                     {"message_id": message_id, "artifact_id": artifact_id},
                     entity_id=message_id, parent_id=message.parent_id)
        return True

    # ---------------------------------------------------------------------- #
    # Title                                                                    #
    # ---------------------------------------------------------------------- #

    def change_title(self, new_title: str) -> None:
        old_title = self.title
        self.title = new_title
        self.updated_at = time.time()
        self._record(EventType.TITLE_CHANGED, None,
                     {"old_title": old_title, "new_title": new_title})

    # ---------------------------------------------------------------------- #
    # Artifact helpers                                                         #
    # ---------------------------------------------------------------------- #

    def get_message_artifacts(self, message_id: str) -> List:
        """Return artifacts attached to a message."""
        message = self.get_message(message_id)
        if not message:
            return []
        return list(message.artifacts or [])

    def get_all_artifacts(self) -> List:
        """Return all artifacts across every message."""
        artifacts = []
        for message in self.messages:
            artifacts.extend(message.artifacts or [])
        return artifacts
