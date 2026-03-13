# AI & Agent Integration (MCP)

The **Supernote Knowledge Hub** includes a built-in [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server. This allows AI agents (like Claude, ChatGPT, or local LLMs) to securely interact with your handwritten notes, perform semantic searches, and retrieve synthesized insights.

## Why use MCP with Supernote?

Handwritten notes are often "dead data"—captured once and rarely revisited. By exposing your notes via MCP, you can:
- **Chat with your notes**: Ask questions like "What was the feedback I wrote during the client meeting last Tuesday?"
- **Synthesize across notebooks**: Ask an agent to "Find all references to 'Project Phoenix' across all my 2024 journals and summarize the timeline."
- **Automate Workflows**: Let an agent extract action items from your handwriting and add them to your task manager.

## Connection & Setup

The Supernote MCP server is available at:
`http://<your-server-ip>:8081/mcp` (using Streamable HTTP).

> [!NOTE]
> The MCP service runs on port `8081` by default, while the main Supernote Hub web interface and OAuth endpoints run on `8080`.

### Authentication

Two authentication methods are supported:

#### Option A — API Keys (recommended for simple setups)

API keys are long-lived tokens you generate once from the Supernote Hub web interface and paste into your MCP client config. They require no OAuth flow or browser interaction.

**Generating a key:**
1. Log in to the Supernote Hub web interface.
2. Click the **key icon** (🔑) in the top-right header, next to the system status icon.
3. Enter a name for the key (e.g. "Claude Desktop") and click **Create**.
4. Copy the key — it is shown **only once** and cannot be retrieved later.

Keys start with the `snmcp_` prefix. They are stored as SHA-256 hashes on the server, so a compromised database does not expose usable credentials.

**Revoking a key:**
Open the same panel and click **Revoke** next to the key. The panel also shows the last time each key was used.

#### Option B — IndieAuth / OAuth 2.1

Supernote Hub implements modern **Dynamic OAuth 2.1** (IndieAuth style). This is suitable for agents that can drive a browser-based OAuth flow.

- **Client ID**: Your Client ID should be a URL identifying the application or agent (e.g., `https://<your home assistant url>`).
- **Dynamic Registration**: You don't need to pre-register clients. The server will dynamically recognize and authorize clients based on their URL.
- **Login**: When an agent requests access, you will be redirected to the Supernote Hub login page to authorize the session.

## Configuration for Popular Agents

### 1. Claude Desktop (API key)

Generate an API key as described above, then add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "supernote": {
      "command": "mcp-proxy",
      "args": ["http://localhost:8081/mcp"],
      "env": {
        "MCP_BEARER_TOKEN": "snmcp_your_key_here"
      }
    }
  }
}
```

### 2. Claude Desktop (OAuth / IndieAuth)

If you prefer the OAuth flow (no static key):

```json
{
  "mcpServers": {
    "supernote": {
      "command": "mcp-proxy",
      "args": ["http://localhost:8081/mcp"]
    }
  }
}
```

### 3. Custom Agents (API key)

Pass the key as a standard `Authorization: Bearer` header:

```python
import httpx

headers = {"Authorization": "Bearer snmcp_your_key_here"}
response = httpx.post("http://localhost:8081/mcp", headers=headers, ...)
```

### 4. Custom Agents (IndieAuth)

When building a custom agent that drives the OAuth flow, use your application's URL as the `client_id`:

```python
# Example OAuth request
params = {
    "response_type": "code",
    "client_id": "https://my-agent-app.com",
    "redirect_uri": "https://my-agent-app.com/callback",
    "scope": "supernote:all",
    "state": "xyz"
}
```

## Available Tools

The MCP server exposes specialized "Tools" that LLMs can call to explore your knowledge:

- `search_notebook_chunks`: Semantic search for content chunks across all notebooks (supports filtering by name and date).
- `get_notebook_transcript`: Retrieve the full AI-generated transcript or specific page ranges for a notebook.

---

> [!TIP]
> **Privacy First**: Your notes never leave your server except for the specific data requested by the AI agent during a session. All vector embeddings and indices stay on your local storage.
