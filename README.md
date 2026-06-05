# Browser Use on Render

Deploy a simple Python API that runs Browser Use tasks on demand.

## What you get

- A FastAPI service with `POST /run` to execute a task and `GET /health` for checks.
- A `render.yaml` blueprint ready for one-click deploys.

## Deploy to Render

1. Fork this repo.
2. In the Render dashboard, choose Blueprint and select your fork.
3. Add `BROWSER_USE_API_KEY` during setup.
4. Deploy.

## Environment variables

`LLM_PROVIDER`: LLM provider to use. Defaults to `anthropic`. Supported values: `browser_use`, `openai`, `anthropic`, `google`. OpenAI is recommended for best reliability on Render.

`LLM_MODEL`: Model name for the selected provider. Required for most providers.

`BROWSER_USE_API_KEY`: Your Browser Use Cloud API key. Required when `LLM_PROVIDER=browser_use`. [Browser Use quickstart](https://docs.browser-use.com/quickstart)

Other provider keys are optional and only required when selected. Supported values and required vars are listed in the Browser Use docs. [Supported models](https://docs.browser-use.com/supported-models)

### Using a local .env file

Copy the example and fill in the values:

```
cp env.example .env
```

Then edit `.env` with your preferred provider:

```bash
# Recommended: OpenAI (most reliable on Render)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=your_key_here

# Alternative: Anthropic
# LLM_PROVIDER=anthropic
# LLM_MODEL=claude-3-5-sonnet-latest
# ANTHROPIC_API_KEY=your_key_here

# Alternative: Google
# LLM_PROVIDER=google
# LLM_MODEL=gemini-2.0-flash
# GOOGLE_API_KEY=your_key_here
```

## API usage

Run a task:

```
curl -X POST "$SERVICE_URL/run" \
  -H "Content-Type: application/json" \
  -d '{"task":"Find the number 1 post on Show HN"}'
```

Get the full agent result:

```
curl -X POST "$SERVICE_URL/run" \
  -H "Content-Type: application/json" \
  -d '{"task":"Find the number 1 post on Show HN","response_mode":"full"}'
```

Health check:

```
curl "$SERVICE_URL/health"
```

## Example queries

Get the top trending repo on GitHub:

```bash
curl -X POST "$SERVICE_URL/run" \
  -H "Content-Type: application/json" \
  -d '{"task":"Go to github.com/trending and tell me the #1 trending repo"}'
```

Check the top story on Hacker News:

```bash
curl -X POST "$SERVICE_URL/run" \
  -H "Content-Type: application/json" \
  -d '{"task":"Go to news.ycombinator.com and tell me the title of the #1 story"}'
```

Search and summarize:

```bash
curl -X POST "$SERVICE_URL/run" \
  -H "Content-Type: application/json" \
  -d '{"task":"Search Google for the latest SpaceX launch and summarize what you find"}'
```

Fill out a form:

```bash
curl -X POST "$SERVICE_URL/run" \
  -H "Content-Type: application/json" \
  -d '{"task":"Go to httpbin.org/forms/post and fill out the form with fake data, then submit it"}'
```

## Example use cases

- Collect a daily summary of a page that changes often.
- Find and extract the top item from a list or table.
- Verify a UI flow and report any errors.
- Log in to a site and capture a specific value for a report.

## Local development

1. Install dependencies:

```
pip install -r requirements.txt
```

2. Set your key:

```
export BROWSER_USE_API_KEY=...
```

3. Run the server:

```
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Docker (optional)

This repo includes a Dockerfile based on the Playwright Python image so Chromium and dependencies are already available.

## Render plan recommendations

This template runs Chromium inside the container, which requires memory. Here's what to expect:

| Plan     | RAM    | Best for                                           |
| -------- | ------ | -------------------------------------------------- |
| Free     | 512 MB | Simple sites (GitHub, Hacker News, static pages)   |
| Starter  | 512 MB | Same as Free, with more CPU for faster processing  |
| Standard | 2 GB   | Heavy JavaScript sites (weather.com, complex SPAs) |

> **Note:** Sites with heavy JavaScript, anti-bot measures, or lots of ads may show empty pages or time out on the Free and Starter tiers. If you encounter this, try the Standard plan.

### LLM provider notes

- **OpenAI** is the most reliable provider from Render's network.
- **Anthropic** may experience intermittent connection timeouts on lower-tier plans.
- **Browser Use Cloud** offloads browser execution to their servers, reducing memory usage on your Render instance.

## Notes

- This template uses the Python example from the Browser Use quickstart. [Browser Use quickstart](https://docs.browser-use.com/quickstart)
