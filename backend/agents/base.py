"""Shared Semantic Kernel Agent wrapper supporting ConcurrentOrchestration."""

from __future__ import annotations

import json
from collections.abc import AsyncIterable, Callable, Coroutine
from typing import Any

from pydantic import ConfigDict, Field
from semantic_kernel import Kernel
from semantic_kernel.agents import Agent, AgentResponseItem, AgentThread, ChatHistoryAgentThread
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.streaming_chat_message_content import StreamingChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole

from orchestration.state import SharedChangeState


class StateAwareSKAgent(Agent):
    """Semantic Kernel Agent adapter connecting SharedChangeState to ConcurrentOrchestration."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    state: SharedChangeState = Field(...)
    runner: Callable[[SharedChangeState, Kernel], Coroutine[Any, Any, dict[str, Any]]] = Field(...)

    async def get_response(
        self,
        messages: str | ChatMessageContent | list[str | ChatMessageContent] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any,
    ) -> AgentResponseItem[ChatMessageContent]:
        active_thread = await self._ensure_thread_exists_with_messages(
            messages=messages,
            thread=thread,
            construct_thread=ChatHistoryAgentThread,
            expected_type=ChatHistoryAgentThread,
        )
        result = await self.runner(self.state, self.kernel)
        reply = ChatMessageContent(
            role=AuthorRole.ASSISTANT,
            name=self.name,
            content=json.dumps(result, default=str),
        )
        await active_thread.on_new_message(reply)
        return AgentResponseItem(message=reply, thread=active_thread)

    async def invoke(
        self,
        messages: str | ChatMessageContent | list[str | ChatMessageContent] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any,
    ) -> AsyncIterable[AgentResponseItem[ChatMessageContent]]:
        item = await self.get_response(messages=messages, thread=thread, **kwargs)
        yield item

    async def invoke_stream(
        self,
        messages: str | ChatMessageContent | list[str | ChatMessageContent] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any,
    ) -> AsyncIterable[AgentResponseItem[StreamingChatMessageContent]]:
        item = await self.get_response(messages=messages, thread=thread, **kwargs)
        stream_msg = StreamingChatMessageContent(
            role=AuthorRole.ASSISTANT,
            name=self.name,
            choice_index=0,
            content=str(item.message.content),
        )
        yield AgentResponseItem(message=stream_msg, thread=item.thread)

