import glob
import logging
import os

from browser_use import Agent, ChatBrowserUse
from browser_use.browser import BrowserSession
from browser_use.llm.base import BaseChatModel
from browser_use.llm import ChatAnthropic, ChatGoogle, ChatOpenAI
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Browser Use API", version="0.1.0")


def find_chromium_binary() -> str | None:
    """Search common Playwright cache locations for Chromium binary."""
    roots = []
    env_root = os.getenv("PLAYWRIGHT_BROWSERS_PATH")
    if env_root:
        roots.append(env_root)
    roots.extend(
        [
            "/ms-playwright",
            "/root/.cache/ms-playwright",
            os.path.expanduser("~/.cache/ms-playwright"),
        ]
    )
    # Playwright uses chrome-linux64 on newer versions, chrome-linux on older
    subdirs = ["chrome-linux64", "chrome-linux"]
    for root in roots:
        for subdir in subdirs:
            pattern = os.path.join(root, "chromium-*", subdir, "chrome")
            matches = sorted(glob.glob(pattern))
            if matches:
                return matches[-1]
    return None


@app.on_event("startup")
async def startup_event():
    """Log browser detection info on startup."""
    logger.info("=== Browser Use API Starting ===")
    logger.info(f"PLAYWRIGHT_BROWSERS_PATH={os.getenv('PLAYWRIGHT_BROWSERS_PATH')}")
    logger.info(f"HOME={os.getenv('HOME')}")

    # Check if /ms-playwright exists
    if os.path.exists("/ms-playwright"):
        try:
            contents = os.listdir("/ms-playwright")
            logger.info(f"/ms-playwright contents: {contents}")
        except Exception as e:
            logger.error(f"Error listing /ms-playwright: {e}")
    else:
        logger.warning("/ms-playwright DOES NOT EXIST")

    # Try to find chromium
    chromium = find_chromium_binary()
    if chromium:
        logger.info(f"Found Chromium at: {chromium}")
    else:
        logger.error("Chromium NOT FOUND - browser tasks will fail")


class RunRequest(BaseModel):
    task: str = Field(..., min_length=1, description="Task to run in the browser.")
    response_mode: str = Field(
        "summary",
        description="summary returns extracted content; full returns full agent result.",
    )


class RunResponse(BaseModel):
    status: str
    result: object | None
    extracted_content: str | None
    error: str | None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def get_llm() -> BaseChatModel:
    # Do not silently fall back to Browser Use Cloud.
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()

    logger.info("Configured LLM_PROVIDER=%r", provider)

    if not provider:
        raise HTTPException(
            status_code=500,
            detail="LLM_PROVIDER is not set. Configure it in the Render dashboard.",
        )

    if provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        model = os.getenv("LLM_MODEL")
        base_url = os.getenv("ANTHROPIC_BASE_URL")

        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="ANTHROPIC_API_KEY is not set.",
            )

        if not model:
            raise HTTPException(
                status_code=500,
                detail="LLM_MODEL is not set.",
            )

        if not base_url:
            raise HTTPException(
                status_code=500,
                detail="ANTHROPIC_BASE_URL is not set.",
            )

        logger.info(
            "Using Azure Foundry Claude deployment: model=%s, base_url=%s",
            model,
            base_url,
        )

        return ChatAnthropic(
            api_key=api_key,
            model=model,
            base_url=base_url.rstrip("/"),
            temperature=0.0,
        )

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("LLM_MODEL")

        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="OPENAI_API_KEY is not set.",
            )

        if not model:
            raise HTTPException(
                status_code=500,
                detail="LLM_MODEL is not set.",
            )

        return ChatOpenAI(
            api_key=api_key,
            model=model,
        )  # type: ignore[call-arg]

    if provider == "google":
        api_key = os.getenv("GOOGLE_API_KEY")
        model = os.getenv("LLM_MODEL")

        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="GOOGLE_API_KEY is not set.",
            )

        if not model:
            raise HTTPException(
                status_code=500,
                detail="LLM_MODEL is not set.",
            )

        return ChatGoogle(
            api_key=api_key,
            model=model,
        )  # type: ignore[call-arg]

    # Optional. Use this only when you deliberately want Browser Use Cloud.
    if provider == "browser_use":
        api_key = os.getenv("BROWSER_USE_API_KEY")

        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="BROWSER_USE_API_KEY is not set.",
            )

        return ChatBrowserUse(api_key=api_key)

    raise HTTPException(
        status_code=500,
        detail=f"Unsupported LLM_PROVIDER: {provider}",
    )


def get_browser_session() -> BrowserSession:
    """Create a BrowserSession optimized for Docker/low-memory environments."""
    chromium_path = find_chromium_binary()
    logger.info(f"get_browser_session: chromium_path={chromium_path}")

    # Extra Chrome flags to reduce memory usage on constrained environments (512MB)
    memory_saving_args = [
        "--disable-gpu",  # No GPU compositing
        "--disable-software-rasterizer",
        "--disable-background-networking",
        "--disable-default-apps",
        "--disable-sync",
        "--disable-translate",
        "--no-first-run",
        "--disable-hang-monitor",
        "--disable-client-side-phishing-detection",
        "--disable-component-update",
        "--disable-breakpad",  # Disable crash reporter
        "--disable-ipc-flooding-protection",
        "--renderer-process-limit=1",  # Limit renderer processes
        "--js-flags=--max-old-space-size=128",  # Limit JS heap to 128MB
    ]

    # Optimize for Docker/Render 512MB tier:
    # - disable extensions to skip downloads and reduce memory
    # - chromium_sandbox=False ensures Docker-friendly Chrome flags
    # - smaller viewport = smaller screenshots = faster LLM calls + less memory
    session = BrowserSession(
        executable_path=chromium_path,
        headless=True,
        enable_default_extensions=False,  # Skip uBlock, cookie banner, etc.
        chromium_sandbox=False,  # Adds --no-sandbox, --disable-dev-shm-usage, etc.
        window_size={"width": 800, "height": 600},  # Minimal viewport for low memory
        args=memory_saving_args,
    )
    logger.info(
        f"BrowserSession created: executable_path={session.browser_profile.executable_path}, "
        f"chromium_sandbox={session.browser_profile.chromium_sandbox}, "
        f"window_size=800x600, extra_args={len(memory_saving_args)}"
    )
    return session


@app.post("/run", response_model=RunResponse)
async def run_task(payload: RunRequest) -> RunResponse:
    try:
        llm = get_llm()
        # Keep agent setup minimal to make API calls predictable.
        browser_session = get_browser_session()
        agent = Agent(task=payload.task, llm=llm, browser_session=browser_session)
        result = await agent.run()
        extracted_content = None
        error_message = None

        # Normalize and read the latest extracted content from history.
        history = None
        if hasattr(result, "model_dump"):
            try:
                result = result.model_dump()
            except Exception:
                pass
        if isinstance(result, dict):
            history = result.get("history")
        else:
            history = getattr(result, "history", None)

        if isinstance(history, list):
            for item in reversed(history):
                step_result = None
                if isinstance(item, dict):
                    step_result = item.get("result", [])
                else:
                    step_result = getattr(item, "result", None)

                if not isinstance(step_result, list):
                    continue

                for entry in reversed(step_result):
                    if isinstance(entry, dict):
                        extracted_content = entry.get("extracted_content")
                        error_message = entry.get("error")
                    else:
                        extracted_content = getattr(entry, "extracted_content", None)
                        error_message = getattr(entry, "error", None)
                    if extracted_content or error_message:
                        break
                if extracted_content or error_message:
                    break
        # summary mode keeps payloads small; full mode returns raw agent output.
        if payload.response_mode == "full":
            return RunResponse(
                status="completed",
                result=result,
                extracted_content=extracted_content,
                error=error_message,
            )
        return RunResponse(
            status="completed",
            result=None,
            extracted_content=extracted_content,
            error=error_message,
        )
    except Exception as exc:
        logging.exception("Agent run failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

