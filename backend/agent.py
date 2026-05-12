import json
from datetime import datetime, timezone
from typing import Any, Literal

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from .config import Settings, get_settings
from .drive_tool import DriveSearchTool


SUPPORTED_MIME_HINTS = """
Common Google Drive q filters:
- PDFs: mimeType='application/pdf'
- Google Docs: mimeType='application/vnd.google-apps.document'
- Google Sheets: mimeType='application/vnd.google-apps.spreadsheet'
- Images: mimeType contains 'image/'
- Text files: mimeType='text/plain'
- Exact name: name = 'Quarterly Report.pdf'
- Partial name: name contains 'report'
- Content search: fullText contains 'invoice'
- Modified after: modifiedTime > 'YYYY-MM-DDT00:00:00'
- Modified before: modifiedTime < 'YYYY-MM-DDT23:59:59'
"""


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str = "default"


class ChatResponse(BaseModel):
    answer: str
    files: list[dict[str, Any]] = Field(default_factory=list)
    generated_query: str | None = None
    raw_tool_output: dict[str, Any] | None = None


def get_chat_model(settings: Settings | None = None) -> Any:
    settings = settings or get_settings()

    if settings.llm_provider == "gemini":
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini.")
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0.1,
        )

    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER=openai.")
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, temperature=0.1)

    if settings.llm_provider == "groq":
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is required when LLM_PROVIDER=groq.")
        from langchain_groq import ChatGroq

        return ChatGroq(model=settings.groq_model, api_key=settings.groq_api_key, temperature=0.1)

    raise RuntimeError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")


def serialize_history(history: list[dict[str, str]]) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    for item in history[-12:]:
        role = item.get("role")
        content = item.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    return messages


def extract_drive_output(intermediate_steps: list[Any]) -> dict[str, Any] | None:
    for step in reversed(intermediate_steps or []):
        if not isinstance(step, tuple) or len(step) != 2:
            continue
        action, observation = step
        tool_name = getattr(action, "tool", "")
        if tool_name == "drive_search":
            if isinstance(observation, dict):
                return observation
            if isinstance(observation, str):
                try:
                    return json.loads(observation)
                except json.JSONDecodeError:
                    return {"raw": observation}
    return None


class DriveDiscoveryAgent:
    def __init__(self, settings: Settings | None = None, tools: list[BaseTool] | None = None) -> None:
        self.settings = settings or get_settings()
        self.tools = tools or [DriveSearchTool()]
        self.llm = get_chat_model(self.settings)
        self.executor = self._build_executor()

    def _build_executor(self) -> AgentExecutor:
        today = datetime.now(timezone.utc).date().isoformat()
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are an AI-powered Google Drive File Discovery Assistant. "
                        "You translate natural language into precise Google Drive API q query fragments, "
                        "call the drive_search tool, and answer conversationally.\n\n"
                        "Rules:\n"
                        "1. Always use drive_search for file discovery requests.\n"
                        "2. Never include the parent folder restriction yourself; the tool adds it.\n"
                        "3. Generate valid Google Drive q syntax only. Use single quotes for literals.\n"
                        "4. Prefer name contains for broad title requests and name = for exact filename requests.\n"
                        "5. Use fullText contains for content/topic requests.\n"
                        "6. Use modifiedTime comparisons for recency and date filters. Current UTC date is {today}.\n"
                        "7. For follow-ups like 'only recent ones', use chat history to refine the previous search.\n"
                        "8. If the user is ambiguous, make a reasonable broad query and explain the interpretation.\n"
                        "9. Keep the final answer short and include the number of matching files.\n\n"
                        "{mime_hints}"
                    ),
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        ).partial(today=today, mime_hints=SUPPORTED_MIME_HINTS)

        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=False,
            return_intermediate_steps=True,
            handle_parsing_errors=True,
            max_iterations=4,
        )

    async def chat(self, message: str, history: list[dict[str, str]] | None = None) -> ChatResponse:
        chat_history = serialize_history(history or [])
        result = await self.executor.ainvoke({"input": message, "chat_history": chat_history})
        drive_output = extract_drive_output(result.get("intermediate_steps", []))
        files = drive_output.get("results", []) if drive_output else []
        generated_query = drive_output.get("query") if drive_output else None

        return ChatResponse(
            answer=result.get("output", "I could not produce a response."),
            files=files,
            generated_query=generated_query,
            raw_tool_output=drive_output,
        )
