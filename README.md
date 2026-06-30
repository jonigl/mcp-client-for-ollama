<p align="center">

  <img src="https://github.com/jonigl/mcp-client-for-ollama/blob/main/misc/ollmcp-logo-512.png?raw=true" width="256" />
</p>
<p align="center">
<i>A simple yet powerful Python client for interacting with Model Context Protocol (MCP) servers using Ollama, allowing you to harness local LLMs for advanced tool execution.</i>
</p>

---

# MCP Client for Ollama (ollmcp)

![PyPI - Downloads](https://img.shields.io/pypi/dm/mcp-client-for-ollama?cacheSeconds=1)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyPI - Python Version](https://img.shields.io/pypi/v/ollmcp?label=ollmcp)](https://pypi.org/project/ollmcp/)
[![PyPI - Python Version](https://img.shields.io/pypi/v/mcp-client-for-ollama?label=mcp-client-for-ollama)](https://pypi.org/project/mcp-client-for-ollama/)
[![CI](https://github.com/jonigl/mcp-client-for-ollama/actions/workflows/ci.yml/badge.svg)](https://github.com/jonigl/mcp-client-for-ollama/actions/workflows/ci.yml)

<p align="center">
  <img src="https://raw.githubusercontent.com/jonigl/mcp-client-for-ollama/v0.27.0/misc/ollmcp-demo.gif" alt="MCP Client for Ollama Demo">
</p>
<p align="center">
  <a href="https://asciinema.org/a/875917" target="_blank">🎥 Watch this demo as an Asciinema recording</a>
</p>

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Installation options](#installation-options)
  - [Troubleshooting](#troubleshooting)
- ✨**NEW** [Managing MCP Servers via CLI](#managing-mcp-servers-via-cli)
    - [mcp add options](#mcp-add-options)
    - [Scopes](#scopes)
  - [Command-line Arguments](#command-line-arguments)
    - [MCP Server Configuration](#mcp-server-configuration)
    - ✨**NEW** [Inference Provider Configuration](#inference-provider-configuration)
    - [General Options](#general-options)
  - ✨**NEW** [Supported Inference Providers](#supported-inference-providers)
    - [API key resolution order](#api-key-resolution-order)
  - [Usage Examples](#usage-examples)
  - [How Tool Calls Work](#how-tool-calls-work)
  - [Agent Mode](#agent-mode)
- [Interactive Commands](#interactive-commands)
  - [MCP Tools](#mcp-tools)
  - [MCP Prompts](#mcp-prompts)
  - [MCP Resources](#mcp-resources)
  - ✨**NEW** [Answer Display Modes](#answer-display-modes)
  - [Input Mode](#input-mode)
  - [Model Selection](#model-selection)
  - [Advanced Model Configuration](#advanced-model-configuration)
  - ✨**NEW** [Thinking Mode and Reasoning Effort](#thinking-mode-and-reasoning-effort)
  - [Server Reloading for Development](#server-reloading-for-development)
  - [Human-in-the-Loop (HIL) Tool Execution](#human-in-the-loop-hil-tool-execution)
    - [Human-in-the-Loop (HIL) Configuration](#human-in-the-loop-hil-configuration)
  - [Performance Metrics](#performance-metrics)
  - [History Management](#history-management)
- [Autocomplete and Prompt Features](#autocomplete-and-prompt-features)
  - [Typer Shell Autocompletion](#typer-shell-autocompletion)
  - [FZF-style Autocomplete](#fzf-style-autocomplete)
  - [MCP Prompts Autocomplete](#mcp-prompts-autocomplete)
  - [Contextual Prompt](#contextual-prompt)
- [Configuration Management](#configuration-management)
  - ✨**NEW** [Per-provider profiles](#per-provider-profiles)
- [Server Configuration Format](#server-configuration-format)
  - [Tips: Where to Put MCP Server Configs and a Working Example](#tips-where-to-put-mcp-server-configs-and-a-working-example)
- [Compatible Models](#compatible-models)
  - [Ollama Cloud Models](#ollama-cloud-models)
- [Where Can I Find More MCP Servers?](#where-can-i-find-more-mcp-servers)
- [Related Projects](#related-projects)
- [License](#license)
- [Acknowledgments](#acknowledgments)

## Overview

MCP Client for Ollama (ollmcp) is a modern, interactive terminal application (TUI) built for harness engineering, connecting local Ollama LLMs to one or more Model Context Protocol (MCP) servers. By fully supporting the core MCP primitives (tools, prompts, and resources), it provides a controlled terminal space where you steer, and the agent executes. With a rich, user-friendly interface, it lets you safely manage your setup in real time with no coding required. Whether you're building, testing, or exploring, this client streamlines your workflow with features like fuzzy autocomplete, advanced model configuration, MCP server hot-reloading for rapid development, and strict Human-in-the-Loop safety controls.

## Features

- 🤖 **Agent Mode**: Iterative tool execution when models request multiple tool calls, with a configurable loop limit and interactive choices when the limit is reached (continue, wrap up, or abort)
- 🌐 **Multi-Server Support**: Connect to multiple MCP servers simultaneously
- 🚀 **Multiple Transport Types**: Supports STDIO, SSE, and Streamable HTTP server connections
- 📋 **MCP Prompts Support**: Browse, invoke, and manage prompts from MCP servers with argument collection, preview, and safe rollback
- 📦 **MCP Resources Support**: Browse and read contextual data from MCP servers including files, documents, and structured data
- ☁️ **Ollama Cloud Support**: Works seamlessly with Ollama Cloud models for tool calling, enabling access to powerful cloud-hosted models while using local MCP tools
- 🌍 **Multiple LLM Providers**: Use Ollama (default) or OpenAI-compatible providers (OpenAI, OpenRouter, DeepSeek, etc.), with connection settings remembered per provider
- 🎨 **Rich Terminal Interface**: Interactive console UI with modern styling
- 🌊 **Streaming Responses**: View model outputs in real-time as they're generated
- 📝 **Answer Display Modes**: Switch between Plain, Markdown, Both, or Markdown (blocks) response views while streaming
- 🛠️ **Tool Management**: Enable/disable specific tools or entire servers during chat sessions
- 🧑‍💻 **Human-in-the-Loop (HIL)**: Review and approve tool executions before they run for enhanced control and safety
- 🎮 **Advanced Model Configuration**: Fine-tune 15+ model parameters including context window size, temperature, sampling, repetition control, and more
- 💬 **System Prompt Customization**: Define and edit the system prompt to control model behavior and persona
- 🧠 **Context Window Control**: Adjust the context window size (num_ctx) to handle longer conversations and complex tasks
- 🎨 **Enhanced Tool Display**: Beautiful, structured visualization of tool executions with JSON syntax highlighting
- 🧠 **Context Management**: Control conversation memory with configurable retention settings
- 🤔 **Thinking Mode**: Advanced reasoning capabilities with visible thought processes for supported models (e.g., gpt-oss, deepseek-r1, qwen3, etc.)
- 💪 **Reasoning Effort Levels**: Set reasoning effort to auto, minimal, low, medium, high, or xhigh for supported models
- 🖼️ **Vision Tool Support**: Images returned by tools are automatically forwarded to vision-capable models
 - 🗣️ **Cross-Language Support**: Seamlessly work with both Python and JavaScript MCP servers
 - 📜 **History Management**: View full conversation history, export to JSON for backup/analysis, and import previous sessions for continuity
- 🔍 **Auto-Discovery**: Automatically find and use Claude's existing MCP server configurations
- 🔁 **Dynamic Model Switching**: Switch between any installed Ollama model without restarting
- 💾 **Configuration Persistence**: Save and load tool preferences and model settings between sessions
- 🔄 **Server Reloading**: Hot-reload MCP servers during development without restarting the client
- ✨ **Fuzzy Autocomplete**: Interactive, arrow-key command autocomplete with descriptions
- 🏷️ **Dynamic Prompt**: Shows current model, thinking mode, and enabled tools
- 📊 **Performance Metrics**: Detailed model performance data after each query, including duration timings and token counts
- 🔌 **Plug-and-Play**: Works immediately with standard MCP-compliant tool servers
- 🔔 **Update Notifications**: Automatically detects when a new version is available
- 🖥️ **Modern CLI with Typer**: Grouped options, shell autocompletion, and improved help output
- ⏹️ **Abort Generation**: You can abort model generation at any time by pressing 'a' during response streaming

## Requirements

- **Python 3.11+** ([Installation guide](https://www.python.org/downloads/))
- **Ollama** running locally ([Installation guide](https://ollama.com/download))
  - After installation, run `ollama list` to see available models. If no models are installed, you can pull one using `ollama pull <model_name>`. For example, `ollama pull gemma4:latest`.
- **UV package manager** ([Installation guide](https://github.com/astral-sh/uv))

## Quick Start

Install `ollmcp` via pip, add an MCP server, and run the client:

```bash
# Install ollmcp via uv
uv tool install --upgrade ollmcp
# or via pip
pip install --upgrade ollmcp
# Add an MCP server (example: playwright stdio server)
ollmcp mcp add playwright -- npx @playwright/mcp@latest
# Run the client (check optional flags with `ollmcp --help`)
ollmcp # once running, use /help for interactive commands
```

## Installation Options

**Option 1:** Install with uv and run (recommended)

```bash
uv tool install --upgrade ollmcp
ollmcp
```

**Option 2:** Install with pip and run

```bash
pip install --upgrade ollmcp
ollmcp
```

**Option 2:** Only run without installing (requires `uv` package manager)

```bash
uvx ollmcp
```

**Option 3:** Install from source and run using virtual environment

```bash
git clone https://github.com/jonigl/mcp-client-for-ollama.git
cd mcp-client-for-ollama
uv run -m mcp_client_for_ollama
```

## Troubleshooting

### `Could not find a version that satisfies the requirement ollmcp (from versions: none)`

This almost always means the Python you are using is **older than the required 3.11+**. This is common on macOS, where the system Python (`/usr/bin/python3`) or the Xcode-bundled Python can be 3.9 or older. When no release matches `requires-python >= 3.11`, pip filters out every version and reports the misleading "from versions: none".

First check your version:

```bash
python3 --version   # must be 3.11 or newer
```

Then install with a modern Python. The simplest option is `uv`, which fetches a suitable Python for you automatically:

```bash
uv tool install --upgrade ollmcp   # recommended, installs the CLI in an isolated environment
# or, if you prefer pip, make sure to use a Python 3.11+ interpreter:
python3.11 -m pip install --upgrade ollmcp
# Then run the client:
ollmcp
```
Take a look to the [Installation Options](#installation-options).

### `error: externally-managed-environment` (PEP 668)

On recent Debian/Ubuntu (Python 3.12+), the system `pip` is intentionally locked to protect OS-managed packages, so `pip install ollmcp` is blocked. This is a system policy ([PEP 668](https://peps.python.org/pep-0668/)), not an issue with ollmcp. Install it into an isolated environment instead:

```bash
uv tool install --upgrade ollmcp   # recommended, installs the CLI in an isolated environment
# or, if you prefer pip, use a virtual environment:
python3.11 -m venv ollmcp-env
source ollmcp-env/bin/activate
python3.11 -m pip install --upgrade ollmcp
# Then run the client:
ollmcp
```
Take a look to the [Installation Options](#installation-options).

> [!WARNING]
> Avoid `pip install --break-system-packages ollmcp`. It works, but it installs into the system Python and can break packages your OS depends on.

## Managing MCP Servers via CLI

ollmcp can manage its own MCP server configurations directly from the command line, similar to `claude mcp`:

```bash
# Remote servers (Streamable HTTP or SSE)
ollmcp mcp add --transport http <name> <url>
ollmcp mcp add --transport sse <name> <url>

# Local stdio servers - everything after `--` is the command to run
ollmcp mcp add [options] <name> -- <command> [args...]

# List configured servers
ollmcp mcp list

# Remove a server
ollmcp mcp remove <name>

# For more details on options and usage, run:
ollmcp mcp --help
ollmcp mcp add --help
```

**Examples:**

> [!TIP]
> Once you have added some servers, simply running `ollmcp` will connect to them automatically.

```bash
ollmcp mcp add --transport http github https://api.githubcopilot.com/mcp/ --header "Authorization: Bearer $YOUR_GITHUB_PAT"
ollmcp mcp add --transport stdio playwright npx @playwright/mcp@latest
ollmcp mcp add filesystem -- npx -y @modelcontextprotocol/server-filesystem /allowed-dir1 ~/allowed-dir2 # stdio transport by default
ollmcp mcp add --env API_KEY=YOUR_KEY --transport sse my-sse-server http://localhost:8000/sse
```


### mcp add options

- `--transport`, `-t`: `stdio` (default), `sse`, or `http`.
- `--header`, `-H`: HTTP header as `"Name: Value"` for `sse`/`http` servers. Repeatable.
- `--env`, `-e`: Environment variable as `KEY=value` for `stdio` servers. Repeatable.
- `--scope`, `-s`: Where to store the server (see scopes below). Default: `local`.

### Scopes

| Scope     | Loads in              | Shared with team | Stored in |
|-----------|-----------------------|-------------------|-----------|
| `local`   | Current project only  | No                | `~/.config/ollmcp/mcp.local.json` (keyed by project path) |
| `project` | Current project only  | Yes (via VCS)     | `.mcp.json` in the project root |
| `user`    | All your projects     | No                | `~/.config/ollmcp/mcp.json` |

The `project` scope writes a standard `.mcp.json` file at your project root, compatible with Claude Code and other MCP-aware tools. If the same server name exists in multiple scopes, precedence is `local` > `project` > `user`.

> [!NOTE]
> Servers added via `ollmcp mcp add` are always loaded as the base layer. Any flags (`--mcp-server`, `--mcp-server-url`, `--servers-json`, `--claude-desktop`) add on top. To include servers from Claude Desktop, pass `--claude-desktop` explicitly.
>
> If a server with the same name is also provided via one of those flags, both connections are currently opened, but only one is kept active under that name. Avoid reusing a registry server's name in `--mcp-server`/`--mcp-server-url`/`--servers-json`/`--claude-desktop`.

### Command-line Arguments

> [!TIP]
> The CLI now uses `Typer` for a modern experience: grouped options, rich help, and built-in shell autocompletion. Advanced users can use short flags for faster commands. To enable autocompletion, run:
>
> ```bash
> ollmcp --install-completion
> ```
>
> Then restart your shell or follow the printed instructions.

#### MCP Server Configuration:

- `--mcp-server`, `-s`: Path to one or more MCP server scripts (.py or .js). Can be specified multiple times.
- `--mcp-server-url`, `-u`: URL to one or more SSE or Streamable HTTP MCP servers. Can be specified multiple times. See [Common MCP endpoint paths](#common-mcp-endpoint-paths) for typical endpoints.
- `--servers-json`, `-j`: Path to a JSON file with server configurations. See [Server Configuration Format](#server-configuration-format) for details.
- `--claude-desktop`: Load servers from Claude Desktop's config file (`~/Library/Application Support/Claude/claude_desktop_config.json`). Merged with servers added via `ollmcp mcp add` and any other flags.

> [!IMPORTANT]
> **Breaking change:** `--auto-discovery` / `-a` has been replaced by `--claude-desktop`. Additionally, servers added via `ollmcp mcp add` are now always loaded automatically, they are no longer a fallback that disappears when other flags are used. Claude Desktop servers are never loaded automatically; use `--claude-desktop` to include them.

#### Inference Provider Configuration:

- `--model`, `-m` MODEL: Model to use. Default: your saved configuration's model if set, otherwise the first model available in Ollama
- `--provider`, `-p` PROVIDER: LLM provider to use (e.g. `ollama`, `openai`, `openrouter`, `deepseek`). Default: `ollama`
- `--host`, `-H` HOST: LLM host / API base URL. Defaults to Ollama's `http://localhost:11434` for the `ollama` provider, or the provider's own default endpoint otherwise.
- `--api-key`, `-k` KEY: API key for the LLM provider. Also read from the `$OLLMCP_API_KEY` environment variable, which is **provider-agnostic** (it applies to whichever provider you select with `--provider`). Keys passed via `$OLLMCP_API_KEY` are never written to the config file; only keys passed with `--api-key` are saved. Not needed for `ollama`.

> [!NOTE]
> Currently supported providers: `ollama`, `openai`, and any OpenAI-compatible provider (`openrouter`, `deepseek`, `perplexity`, etc.). More providers coming soon.

#### General Options:

- `--version`, `-v`: Show version and exit
- `--help`, `-h`: Show help message and exit
- `--install-completion`: Install shell autocompletion scripts for the client
- `--show-completion`: Show available shell completion options

### Supported Inference Providers

> [!WARNING]
> **Non-Ollama providers are experimental.** Support for providers other than Ollama was added recently and is still being stabilized, not everything may work correctly yet.

ollmcp works with **Ollama** plus any **OpenAI-compatible** provider that [any-llm](https://github.com/mozilla-ai/any-llm) exposes. Select one with `--provider`. Provide the key with `--api-key` or `$OLLMCP_API_KEY` (both work for **any** selected provider) or via the provider's own environment variable shown below. `$OLLMCP_API_KEY` and the provider-native env vars are never written to disk; only a key passed with `--api-key` is saved to the config.

| Provider (`--provider`) | API key env var |
|---|---|
| [`ollama`](https://github.com/ollama/ollama) (default) | - (local) |
| [`azureopenai`](https://learn.microsoft.com/en-us/azure/ai-foundry/) | `AZURE_OPENAI_API_KEY` |
| [`dashscope`](https://bailian.console.aliyun.com/cn-beijing/?tab=api#/api) | `DASHSCOPE_API_KEY` |
| [`databricks`](https://docs.databricks.com/) | `DATABRICKS_TOKEN` |
| [`deepinfra`](https://deepinfra.com/docs/openai_api) | `DEEPINFRA_API_KEY` |
| [`deepseek`](https://platform.deepseek.com/) | `DEEPSEEK_API_KEY` |
| [`fireworks`](https://fireworks.ai/api) | `FIREWORKS_API_KEY` |
| [`gateway`](https://github.com/mozilla-ai/any-llm) | `GATEWAY_API_KEY` |
| [`inception`](https://inceptionlabs.ai/) | `INCEPTION_API_KEY` |
| [`llama`](https://www.llama.com/products/llama-api/) | `LLAMA_API_KEY` |
| [`llamacpp`](https://github.com/ggml-org/llama.cpp) | - (local) |
| [`llamafile`](https://github.com/Mozilla-Ocho/llamafile) | - (local) |
| [`lmstudio`](https://lmstudio.ai/) | `LM_STUDIO_API_KEY` |
| [`minimax`](https://www.minimax.io/platform_overview) | `MINIMAX_API_KEY` |
| [`moonshot`](https://platform.moonshot.ai/) | `MOONSHOT_API_KEY` |
| [`mzai`](https://any-llm.ai) | `ANY_LLM_KEY` |
| [`nebius`](https://studio.nebius.ai/) | `NEBIUS_API_KEY` |
| [`openai`](https://platform.openai.com/docs/api-reference) | `OPENAI_API_KEY` |
| [`openrouter`](https://openrouter.ai/docs) | `OPENROUTER_API_KEY` |
| [`perplexity`](https://docs.perplexity.ai/) | `PERPLEXITY_API_KEY` |
| [`portkey`](https://portkey.ai/docs) | `PORTKEY_API_KEY` |
| [`qiniu`](https://developer.qiniu.com/aitokenapi) | `QINIU_API_KEY` |
| [`sambanova`](https://sambanova.ai/) | `SAMBANOVA_API_KEY` |
| [`vllm`](https://docs.vllm.ai/) | `VLLM_API_KEY` |
| [`zai`](https://docs.z.ai/guides/develop/python/introduction) | `ZAI_API_KEY` |

> [!NOTE]
> Local OpenAI-compatible servers (`ollama`, `llamacpp`, `llamafile`, `lmstudio`, `vllm`) typically run without an API key, point ollmcp at them with `--host`. Providers any-llm offers that are **not** OpenAI-compatible (e.g. `anthropic`, `gemini`, `mistral`, `groq`, `cohere`) are not supported yet.

> [!WARNING]
> **Capability detection limitation:** ollmcp only reads real per-model capabilities (`tools`, `vision`, `thinking`) from Ollama. For every non-Ollama provider, all three capabilities are currently assumed available and shown as such in the model list and badges, so a model may be reported as supporting tools, vision, or thinking even when it doesn't. If a model lacks a capability, the provider's API will return an error when you try to use it.

#### API key resolution order

For the selected provider, ollmcp resolves the API key in this order, from **highest** to **lowest** precedence:

1. The `--api-key` / `-k` flag.
2. The `$OLLMCP_API_KEY` environment variable (provider-agnostic, applies to whichever provider you selected with `--provider`).
3. The per-provider key saved in `~/.config/ollmcp/config.json` (present only if it was once passed via `--api-key`).
4. The provider's own native environment variable, detected by [any-llm](https://github.com/mozilla-ai/any-llm) (e.g. `OPENAI_API_KEY`, `OPENROUTER_API_KEY`).

> [!WARNING]
> A saved per-provider key (3) takes precedence over the provider's native environment variable (4). So if you previously saved a **wrong or expired** key, setting `OPENAI_API_KEY` (or the equivalent) alone will **not** override it. To fix it, either pass the correct key with `--api-key`, or remove the stale `apiKey` from that provider's profile in `~/.config/ollmcp/config.json`.


### Usage Examples

Simplest way to run the client:

```bash
ollmcp
```
> [!TIP]
> This connects to all servers registered via `ollmcp mcp add` and uses the model from your saved configuration file, or the first available model in Ollama if none is saved. Pass `--claude-desktop` to also include servers from Claude Desktop's config.

Connect to a single server:

```bash
ollmcp --mcp-server /path/to/weather.py --model llama3.2:3b
# Or using short flags:
ollmcp -s /path/to/weather.py -m llama3.2:3b
```

Connect to multiple servers:

```bash
ollmcp --mcp-server /path/to/weather.py --mcp-server /path/to/filesystem.js
# Or using short flags:
ollmcp -s /path/to/weather.py -s /path/to/filesystem.js
```

> [!TIP]
> If `--model` is not specified, the model from your saved configuration file is used; otherwise the first available model in Ollama is selected automatically (you'll be told how to pull one if none are installed).

Use a JSON configuration file:

```bash
ollmcp --servers-json /path/to/servers.json --model llama3.2:1b
# Or using short flags:
ollmcp -j /path/to/servers.json -m llama3.2:1b
```

> [!TIP]
> See the [Server Configuration Format](#server-configuration-format) section for details on how to structure the JSON file.

Use a custom Ollama host:

```bash
ollmcp --host http://localhost:22545 --servers-json /path/to/servers.json
# Or using short flags:
ollmcp -H http://localhost:22545 -j /path/to/servers.json
```

Use a different LLM provider (OpenAI or any OpenAI-compatible API):

```bash
ollmcp --provider openai --api-key $OPENAI_API_KEY --model gpt-5.5
# OpenAI-compatible providers (e.g. OpenRouter, DeepSeek); override the endpoint with --host if needed:
ollmcp --provider openrouter --api-key $OPENROUTER_API_KEY -m openrouter/free
```

> [!TIP]
> Provider settings (model, host, API key) are remembered **per provider**. Once saved with `/save-config`, plain `ollmcp` resumes your last-used provider. See [Configuration Management](#configuration-management) for details.

Connect to SSE or Streamable HTTP servers by URL:

```bash
ollmcp --mcp-server-url http://localhost:8000/sse --model qwen2.5:latest
# Or using short flags:
ollmcp -u http://localhost:8000/sse -m qwen2.5:latest
```

Connect to multiple URL servers:

```bash
ollmcp --mcp-server-url http://localhost:8000/sse --mcp-server-url http://localhost:9000/mcp
# Or using short flags:
ollmcp -u http://localhost:8000/sse -u http://localhost:9000/mcp
```

Mix local scripts and URL servers:

```bash
ollmcp --mcp-server /path/to/weather.py --mcp-server-url http://localhost:8000/mcp --model qwen3:1.7b
# Or using short flags:
ollmcp -s /path/to/weather.py -u http://localhost:8000/mcp -m qwen3:1.7b
```

Include Claude Desktop servers alongside other sources:

```bash
ollmcp --mcp-server /path/to/weather.py --mcp-server-url http://localhost:8000/mcp --claude-desktop
# Or using short flags:
ollmcp -s /path/to/weather.py -u http://localhost:8000/mcp --claude-desktop
```

## Interactive Commands

During chat, use these commands:

> [!IMPORTANT]
> **NEW:** Built-in interactive commands now require a leading `/`.
> - Use `/help`, `/model`, `/tools`, `/prompts`, etc.
> - Bare command names like `help` or `model` are no longer executed as commands.
> - Prompt invocations also use `/`, with `/server:prompt_name` recommended to avoid collisions.

![ollmcp main interface](https://github.com/jonigl/mcp-client-for-ollama/blob/main/misc/ollmcp-welcome.png?raw=true)

| Command          | Shortcut         | Description                                         |
|------------------|------------------|-----------------------------------------------------|
| `abort`          | `a`              | While model is generating, abort the current response generation |
| `/clear`         | `/cc`            | Clear conversation history and context              |
| `/cls`           | `/clear-screen`  | Clear the terminal screen                           |
| `/context`       | `/c`             | Toggle context retention                            |
| `/context-info`  | `/ci`            | Display context statistics                          |
| `/export-history`| `/eh`            | Export chat history to a JSON file                  |
| `/full-history`  | `/fh`            | Display all conversation history                    |
| `/help`          | `/h`             | Display help and available commands                 |
| `/import-history`| `/ih`            | Import chat history from a JSON file                |
| `/human-in-the-loop` | `/hil`       | Toggle Human-in-the-Loop confirmations for tool execution |
| `/load-config`   | `/lc`            | Load tool and model configuration from a file       |
| `/loop-limit`    | `/ll`            | Set maximum iterative tool-loop iterations (Agent Mode). Default: 7 |
| `/model`         | `/m`             | List and select a different Ollama model            |
| `/model-config`  | `/mc`            | Configure advanced model parameters and system prompt |
| `/display-mode`  | `/dm`            | Choose Plain, Markdown, Both, or Markdown (blocks) answer display modes |
| `/input-mode`    | `/im`            | Choose Single-line or Multiline chat input mode     |
| `/prompts`       | `/pr`            | Browse and view all available MCP prompts             |
| `/server:prompt_name`   | `/prompt_name`      | Invoke a prompt (qualified is recommended) |
| `/resources`     | `/res`           | Browse and view all available MCP resources         |
| `@uri`           | -                | Read a specific resource by URI (e.g., `@server://info`) |
| `/quit`, `/exit`, `/bye`   | `/q`, `Ctrl+C`, or `Ctrl+D`  | Exit the client                              |
| `/reload-servers`| `/rs`            | Reload all MCP servers with current configuration   |
| `/reset-config`  | `/rc`            | Reset configuration to defaults (all tools enabled) |
| `/save-config`   | `/sc`            | Save current tool and model configuration to a file |
| `/show-metrics`  | `/sm`            | Toggle performance metrics display                  |
| `/show-thinking` | `/st`            | Toggle thinking text visibility (visible by default) |
| `/thinking-mode` | `/tm`            | Toggle thinking mode on supported models            |
| `/reasoning-effort` | `/re`         | Set reasoning effort level (auto/minimal/low/medium/high/xhigh) when thinking mode is on. Default: medium |
| `/show-tool-execution` | `/ste`      | Toggle tool execution display visibility            |
| `/tools`         | `/t`             | Open the tool selection interface                   |


### MCP Tools

The tool and server selection interface allows you to enable or disable specific tools:

![ollmcp tool and server selection interface](https://github.com/jonigl/mcp-client-for-ollama/blob/main/misc/ollmpc-tool-and-server-selection.png?raw=true)

- Enter **numbers** separated by commas (e.g. `1,3,5`) to toggle specific tools
- Enter **ranges** of numbers (e.g. `5-8`) to toggle multiple consecutive tools
- Enter **S + number** (e.g. `S1`) to toggle all tools in a specific server
- `a` or `all` - Enable all tools
- `n` or `none` - Disable all tools
- `d` or `desc` - Show/hide tool descriptions
- `j` or `json` - Show detailed tool JSON schemas on enabled tools for debugging purposes
- `s` or `save` - Save changes and return to chat
- `q` or `quit` - Cancel changes and return to chat


### MCP Prompts

MCP Prompts provide reusable, server-defined conversation starters and context templates. Servers can expose prompts with descriptions, required arguments, and pre-formatted messages that help you quickly start specific types of conversations or inject structured context into your chat.

#### Features

- 📋 **Browse Prompts**: View all available prompts from connected servers with descriptions and argument requirements
- ⚡️ **Quick Invocation**: Use slash syntax to invoke prompts (`/server:prompt_name` recommended)
- 🔤 **Autocomplete**: Type `/` to see prompt suggestions with fuzzy matching
- 📝 **Argument Collection**: Interactive prompts guide you through required parameters
- 👁️ **Preview**: Review prompt content before injection to ensure it fits your needs
- 🎯 **Flexible Injection**: Choose to execute immediately or inject-only (add to history without triggering model)
- 🧠 **Context-Aware**: Automatically adapts behavior based on whether prompt ends with user or assistant message
- 🔄 **Safe Rollback**: Automatic history cleanup if you abort or encounter errors
- 💬 **Text Content**: Supports text-based prompt messages (image/audio/resource support coming soon)

#### How to Use MCP Prompts

**Browse Available Prompts:**
```
/prompts  # or '/pr'
```
This displays all prompts grouped by server, showing their names, required arguments, and descriptions.

**Invoke a Prompt:**
```
/server:prompt_name
```
For example, if a server named `docs` provides a "summarize" prompt:
```
/docs:summarize
```

If a prompt name is unique across connected servers, you can use the short form:
```
/summarize
```

If multiple servers expose the same prompt name, the client will ask you to use the qualified form and suggest valid `/server:prompt_name` options.

**Autocomplete:**
- Type `/` to see all available prompts with descriptions
- Continue typing to filter prompts with fuzzy matching
- Use arrow keys to navigate and press Enter to select

> [!TIP]
> Prompts are discovered automatically when you connect to MCP servers. If a server supports prompts, they'll be available immediately in the `prompts` list and autocomplete.

**Workflow:**
1. Type `/server:prompt_name` (recommended) or select from autocomplete
2. If the prompt requires arguments, you'll be prompted to provide them
3. Review the prompt preview showing what will be injected
4. Choose how to use the prompt:
   - **y/yes** (default): Send the prompt to the model and get a response
     - For prompts ending with a **user message**: Uses that message as the query
     - For prompts ending with an **assistant message**: Adds "Please respond based on the above context." as the query
   - **i/inject**: Just add the prompt to conversation history without triggering the model (lets you type your own query afterward)
   - **n/no**: Cancel and return to chat
5. The prompt is injected based on your choice
6. If you abort during model generation (press 'a'), changes are automatically rolled back

**Example:**
![ollmcp prompt feature screenshot](https://github.com/jonigl/mcp-client-for-ollama/blob/main/misc/ollmcp-prompt-feature.png?raw=true)

> [!WARNING]
> **Content Type Limitations**: MCP Prompts currently support **text content only**. The following content types are not yet supported and will be automatically skipped:
> - 🖼️ **Images** - Image content in prompts
> - 🎵 **Audio** - Audio content in prompts
> - 📦 **Resources** - Embedded resource content

### MCP Resources

MCP Resources provide access to contextual data exposed by MCP servers-files, documents, structured data, and more. Servers can expose resources with metadata (name, description, MIME type) that you can browse and read into your conversation context.

#### Features

- 📋 **Browse Resources**: View all available resources from connected servers with URIs, names, MIME types, and descriptions
- 📖 **Read Resources**: Use `@uri` syntax to read resource content, standalone or inline within a query
- 📝 **Text Content**: Full support for text-based resources (markdown, code, logs, etc.)
- 🖼️ **Vision Image Support**: Image resources (`image/*`) are automatically forwarded as base64 images to vision-capable models
- 🎯 **Context Injection**: Resource content is buffered and injected as context alongside your next query
- 🔍 **Autocomplete**: Type `@` to see available resource and template suggestions with fuzzy matching
- 🛡️ **Binary Safety**: Non-image binary content (audio, video, PDFs, archives) is detected and gracefully skipped with informative messages

#### How to Use MCP Resources

**Browse Available Resources:**
```
/resources  # or '/res'
```
This displays all resources and templates grouped by server, showing URIs, names, MIME types, and descriptions. Binary resources are marked with a `[binary]` tag and templates with a `[template]` tag.

**Read a Resource:**
```
@<uri>
```
For example, to read a file resource:
```
@file:///path/to/document.md
```

There are two ways to use `@uri`:

**1. Standalone (buffer then query):** Type `@uri` on its own. The resource is fetched and buffered. Then type your query on the next prompt. The resource content is injected as context automatically.

**2. Inline (single turn):** Include `@uri` anywhere inside your query text. The resource is fetched and the query is processed immediately in one step.

**Standalone example:**
```
qwen3/show-thinking/6-tools❯ @server://info
✅ Read resource 'get_server_info' (197 chars)

Preview:
This is a simple MCP server with streamable HTTP transport. It supports tools for greeting, adding numbers, generating
random numbers, and calculating BMI. It also provides a BMI calculator prompt.

1 resource(s) buffered. Type your query, or include @another_uri inline.

qwen3/show-thinking/6-tools❯ Next question here
```

**Inline example:**
```
qwen3/show-thinking/6-tools❯ summarize the key features from @server://info
✅ Read resource 'get_server_info' (197 chars)

Preview:
This is a simple MCP server with streamable HTTP transport. It supports tools for greeting, adding numbers, generating
random numbers, and calculating BMI. It also provides a BMI calculator prompt.
[model response]
```

> [!TIP]
> Resources are discovered automatically when you connect to MCP servers. If a server supports resources, they'll be available immediately in the `resources` list and `@` autocomplete.

> [!NOTE]
> 🖼️ **Images** (`image/*`) **are** supported, they are passed directly to vision-capable models as base64 data.
> **Binary Content**: The following resource types are **not** supported as context and will be skipped with an informative message:
> - 🎵 **Audio** - `audio/*` MIME types
> - 📹 **Video** - `video/*` MIME types
> - 📄 **PDFs** - `application/pdf`
> - 🗜️ **Archives** - `application/zip`, `application/octet-stream`
>


### Answer Display Modes

The `display-mode` (`dm`) command lets you choose how model answers are shown while they stream:

- **Plain**: Streams the response once as plain text with no final markdown re-render
- **Markdown**: Renders the response as markdown during streaming with throttled redraws (live; can flicker or duplicate lines with emojis or when you resize the terminal)
- **Both** (default): Streams plain text first, then renders the completed response again as markdown
- ✨**NEW** **Markdown (blocks)**: Renders the response as markdown one block at a time, append-only each paragraph/list/table/code block prints once when it completes and is never redrawn, so it cannot duplicate lines

Use `/display-mode` or `/dm` during chat to open the interactive picker.

**Why you might switch modes:**

- **Plain** is the least noisy option if you want minimal redraw or flicker
- **Markdown** shows live markdown formatting, but its in-place redraws can flicker or duplicate lines with emojis/resizes
- **Both** gives you fast streaming feedback plus a clean final markdown rendering
- **Markdown (blocks)** is the most stable way to see formatted markdown while streaming, at the cost of block-by-block (rather than token-by-token) updates

> [!TIP]
> Your selected display mode is saved with `save-config` and restored with `load-config`, so you can keep different viewing preferences for different workflows.

### Input Mode

The `input-mode` (`im`) command controls how you write chat messages:

- **Single-line** (default): Press **Enter** to send immediately after typing your message
- **Multiline**: Press **Enter** to add a new line, then press **Esc** followed by **Enter** to send the entire message when you're done. This allows for more complex messages with multiple paragraphs or code blocks.
- **Ctrl+J** also inserts a new line in multiline mode as a reliable fallback across terminals

Use `/input-mode` or `/im` during chat to open the interactive picker.

> [!IMPORTANT]
> Multiline send shortcuts can vary by terminal emulator and OS keyboard handling. This client relies on **Esc then Enter** as the portable submit shortcut in multiline mode. **Shift+Enter** and **Meta+Enter** may work in some terminals, but they are not guaranteed.


### Model Selection

The model selection interface shows all available models in your Ollama installation:

![ollmcp model selection interface](https://github.com/jonigl/mcp-client-for-ollama/blob/main/misc/ollmpc-model-selection.jpg?raw=true)

- Enter the **number** of the model you want to use
- `s` or `save` - Save the model selection and return to chat
- `q` or `quit` - Cancel the model selection and return to chat

### Advanced Model Configuration

The `model-config` (`mc`) command opens the advanced model settings interface, allowing you to fine-tune how the model generates responses:

![ollmcp model configuration interface](https://github.com/jonigl/mcp-client-for-ollama/blob/main/misc/ollmcp-model-configuration.png?raw=true)

#### System Prompt

- **System Prompt**: Set the model's role and behavior to guide responses.

#### Key Parameters

- **System Prompt**: Set the model's role and behavior to guide responses.
- **Context Window (num_ctx)**: Set how much chat history the model uses. Balance with memory usage and performance.
- **Keep Tokens**: Prevent important tokens from being dropped
- **Max Tokens**: Limit response length (0 = auto)
- **Seed**: Make outputs reproducible (set to -1 for random)
- **Temperature**: Control randomness (0 = deterministic, higher = creative)
- **Top K / Top P / Min P / Typical P**: Sampling controls for diversity
- **Repeat Last N / Repeat Penalty**: Reduce repetition
- **Presence/Frequency Penalty**: Encourage new topics, reduce repeats
- **Stop Sequences**: Custom stopping points (up to 8)
 - **Batch Size (num_batch)**: Controls internal batching of requests; larger values can increase throughput but use more memory.

#### Commands

- Enter parameter numbers `1-15` to edit settings
- Enter `sp` to edit the system prompt
- Use `u1`, `u2`, etc. to unset parameters, or `uall` to reset all
- `h`/`help`: Show parameter details and tips
- `undo`: Revert changes
- `s`/`save`: Apply changes
- `q`/`quit`: Cancel

#### Example Configurations

- **Factual:** `temperature: 0.0-0.3`, `top_p: 0.1-0.5`, `seed: 42`
- **Creative:** `temperature: 1.0+`, `top_p: 0.95`, `presence_penalty: 0.2`
- **Reduce Repeats:** `repeat_penalty: 1.1-1.3`, `presence_penalty: 0.2`, `frequency_penalty: 0.3`
- **Balanced:** `temperature: 0.7`, `top_p: 0.9`, `typical_p: 0.7`
- **Reproducible:** `seed: 42`, `temperature: 0.0`
- **Large Context:** `num_ctx: 8192` or higher for complex conversations requiring more context

> [!TIP]
> All parameters default to unset, letting Ollama use its own optimized values. Use `help` in the config menu for details and recommendations. Changes are saved with your configuration.


### Thinking Mode and Reasoning Effort

Enable thinking mode with `/thinking-mode` (`/tm`) to activate extended reasoning on supported models (e.g., `qwen3`, `deepseek-r1`, Claude with extended thinking). Use `/show-thinking` (`/st`) to toggle whether the reasoning process is visible in the response.

Use `/reasoning-effort` (`/re`) to control **how much reasoning effort** the model applies when thinking mode is on:

| Level | Description |
|-------|-------------|
| `auto` | Provider's default effort (recommended for cloud) |
| `minimal` | Fastest, least reasoning |
| `low` | Light reasoning |
| `medium` | Balanced — **default** |
| `high` | More thorough reasoning |
| `xhigh` | Maximum reasoning effort |

> [!NOTE]
> Some providers or models may ignore reasoning effort settings.


### Server Reloading for Development

The `reload-servers` command (`rs`) is particularly useful during MCP server development. It allows you to reload all connected servers without restarting the entire client application.

**Key Benefits:**
- 🔄 **Hot Reload**: Instantly apply changes to your MCP server code
- 🛠️ **Development Workflow**: Perfect for iterative development and testing
- 📝 **Configuration Updates**: Automatically picks up changes in server JSON configs or Claude configs
- 🎯 **State Preservation**: Maintains your tool enabled/disabled preferences across reloads
- ⚡️ **Time Saving**: No need to restart the client and reconfigure everything

**When to Use:**
- After modifying your MCP server implementation
- When you've updated server configurations in JSON files
- After changing Claude's MCP configuration
- During debugging to ensure you're testing the latest server version

Simply type `/reload-servers` or `/rs` in the chat interface, and the client will:
1. Disconnect from all current MCP servers
2. Reconnect using the same parameters (servers added via `ollmcp mcp add`, server paths, config files, `--claude-desktop`)
3. Restore your previous tool enabled/disabled settings
4. Display the updated server and tool status

This feature dramatically improves the development experience when building and testing MCP servers.

### Human-in-the-Loop (HIL) Tool Execution

The Human-in-the-Loop feature provides an additional safety layer by allowing you to review and approve tool executions before they run. This is particularly useful for:

- 🛡️ **Safety**: Review potentially destructive operations before execution
- 🔍 **Learning**: Understand what tools the model wants to use and why
- 🎯 **Control**: Selective execution of only the tools you approve
- 🚫 **Prevention**: Stop unwanted tool calls from executing
- 🔄 **Session Mode**: Auto-approve all tools for the current query session
- 🛑 **Query Abort**: Abort entire query without saving to history

#### HIL Confirmation Display

When HIL is enabled, you'll see a confirmation prompt before each tool execution:

**Example:**

![ollmcp HIL confirmation screenshot](https://github.com/jonigl/mcp-client-for-ollama/blob/main/misc/ollmcp-hil-feature.png?raw=true)

#### HIL Confirmation Options

When prompted, you can choose from the following options:

- **y/yes**: Execute this specific tool call
- **n/no**: Skip this tool call and continue with the query
- **s/session**: Execute this and all subsequent tool calls for the current query without further prompts
- **d/disable**: Permanently disable HIL confirmations (can be re-enabled with `hil` command)
- **a/abort**: Abort the entire query immediately without saving to history

> [!TIP]
> The **session** option is particularly useful when the model needs to execute multiple tools in sequence. Instead of confirming each one individually, you can approve all tools for the current query session, then HIL will reset automatically for the next query.

### Human-in-the-Loop (HIL) Configuration

- **Default State**: HIL confirmations are enabled by default for safety
- **Toggle Command**: Use `/human-in-the-loop` or `/hil` to toggle on/off
- **Persistent Settings**: HIL preference is saved with your configuration
- **Quick Disable**: Choose "disable" during any confirmation to turn off permanently
- **Session Auto-Approve**: Use "session" during confirmation to approve all tools for current query
- **Query Abort**: Use "abort" during confirmation to immediately stop the query without saving
- **Re-enable**: Use the `hil` command anytime to turn confirmations back on

**Benefits:**
- **Enhanced Safety**: Prevent accidental or unwanted tool executions
- **Awareness**: Understand what actions the model is attempting to perform
- **Selective Control**: Choose which operations to allow on a case-by-case basis
- **Flexible Workflow**: Session mode for efficient multi-tool queries, individual approval for sensitive operations
- **Clean Abort**: Stop problematic queries immediately without polluting conversation history
- **Peace of Mind**: Full visibility and control over automated actions


### Performance Metrics

The Performance Metrics feature displays detailed model performance data after each query in a bordered panel. The metrics show duration timings, token counts, and generation rates directly from Ollama's response.

**Displayed Metrics:**
- `total duration`: Total time spent generating the complete response (seconds)
- `load duration`: Time spent loading the model (milliseconds)
- `prompt eval count`: Number of tokens in the input prompt
- `prompt eval duration`: Time spent evaluating the input prompt (milliseconds)
- `eval count`: Number of tokens generated in the response
- `eval duration`: Time spent generating the response tokens (seconds)
- `prompt eval rate`: Speed of input prompt processing (tokens/second)
- `eval rate`: Speed of response token generation (tokens/second)

**Example:**
![ollmcp ollama performance metrics screenshot](https://github.com/jonigl/mcp-client-for-ollama/blob/main/misc/ollmcp-ollama-performance-metrics.png?raw=true)

#### Performance Metrics Configuration

- **Default State**: Metrics are disabled by default for cleaner output
- **Toggle Command**: Use `show-metrics` or `sm` to enable/disable metrics display
- **Persistent Settings**: Metrics preference is saved with your configuration

**Benefits:**
- **Performance Monitoring**: Track model efficiency and response times
- **Token Tracking**: Monitor actual token consumption for analysis
- **Benchmarking**: Compare performance across different models

> [!NOTE]
> **Data Source**: All metrics come directly from Ollama's response, ensuring accuracy and reliability.

### History Management

The History Management feature allows you to view, export, and import your conversation history. This is useful for:

- 📜 **Full History View**: Review all conversations from your current session
- 💾 **Export**: Save conversations to JSON files for backup or analysis
- 📥 **Import**: Load previous conversation history to continue where you left off
- 🔄 **Portability**: Share or transfer conversations between sessions

#### History Commands

**View Full History:**
```
full-history  # or 'fh'
```
Displays all conversation history from the current session in a formatted view, showing both queries and responses.

**Export History:**
```
export-history  # or 'eh'
```
Exports your current chat history to a JSON file. You can specify a custom filename or use the default timestamp-based name (e.g., `ollmcp_chat_history_2026-01-05_143022.json`). Files are saved to `~/.config/ollmcp/history/` directory. The command includes file overwrite protection.

**Import History:**
```
import-history  # or 'ih'
```
Imports a previously exported chat history from a JSON file. The command validates the JSON structure to ensure compatibility. Imported history is added to your current conversation context.

**History Storage:**
- Export location: `~/.config/ollmcp/history/`
- Default filename format: `ollmcp_chat_history_YYYY-MM-DD_HHMMSS.json`
- JSON format includes both queries and responses with proper structure validation

**Benefits:**
- **Session Continuity**: Resume conversations across different sessions
- **Backup**: Keep records of important conversations
- **Analysis**: Export history for external analysis or review
- **Sharing**: Share conversation context with team members
- **Testing**: Import test conversations for development and debugging

> [!TIP]
> When exporting, if you don't provide a filename, the system automatically generates a timestamped filename to prevent accidental overwrites.

## Autocomplete and Prompt Features

### Typer Shell Autocompletion

- The CLI supports shell autocompletion for all options and arguments via Typer
- To enable, run `ollmcp --install-completion` and follow the instructions for your shell
- Enjoy tab-completion for all grouped and general options

### FZF-style Autocomplete

- Slash-namespace autocomplete for commands and prompts (`/`)
- Command descriptions shown in the menu
- Case-insensitive matching for convenience
- Centralized command list for consistency
- Plain text query typing is intentionally free of action autocomplete noise

### MCP Prompts Autocomplete

- Type `/` to trigger prompt autocomplete
- Fuzzy matching on prompt names and descriptions
- Supports qualified prompt references like `/server:prompt_name`
- Shows prompt descriptions in the menu
- Prompt arguments are collected during prompt invocation (not shown in autocomplete rows)
- Terminal-width-aware description truncation

### Contextual Prompt

The chat prompt now gives you clear, contextual information at a glance:

- **Model**: Shows the current Ollama model in use
- **Thinking Mode**: Indicates if "thinking mode" is active (for supported models)
- **Tools**: Displays the number of enabled tools

**Example prompt:**
```
qwen3/show-thinking/12-tools❯
```
- `qwen3` Model name
- `/show-thinking` Thinking mode indicator (if enabled, otherwise `/thinking` or omitted)
- `/12-tools` Number of tools enabled (or `/1-tool` for singular)
- `❯` Prompt symbol

This makes it easy to see your current context before entering a query.

> [!TIP]
> Type `/` after the prompt symbol to see autocomplete suggestions for available MCP prompts.

## Configuration Management

> [!TIP]
> Running `ollmcp` with no flags automatically loads the default configuration from `~/.config/ollmcp/config.json` if it exists.

The client saves and loads your preferences between sessions:

- When using `/save-config`, you can provide a name for the configuration or use the default
- Configurations are stored in the `~/.config/ollmcp/` directory
- The default configuration is saved as `~/.config/ollmcp/config.json`
- Named configurations are saved as `~/.config/ollmcp/{name}.json`

### Per-provider profiles

Connection settings are stored **per provider**, so switching providers never reuses another provider's model, host, or API key. Each provider keeps its own:

- **Model** selection
- **Host** / API base URL
- **API key**

The configuration also records a `defaultProvider`. When you run `ollmcp` with no `--provider` flag, it loads that provider's profile; a fresh install starts on `ollama`. Each time you `/save-config`, the provider you're currently using *becomes the new default*, so running plain `ollmcp` resumes wherever you left off. Pass `--provider <name>` at any time to switch to (and load) a different provider's profile, and `--model` / `--host` / `--api-key` override the saved values for that run.

> [!NOTE]
> Only a key passed with `--api-key` is stored, in plain text, in `~/.config/ollmcp/config.json`. Keys provided through the `$OLLMCP_API_KEY` environment variable or a provider's native environment variable (for example `OPENROUTER_API_KEY`) are **never** written to disk, use one of those if you don't want your key persisted.

The following settings are **shared** across all providers:

- Advanced model parameters (system prompt, temperature, sampling settings, etc.)
- Enabled/disabled status of all tools
- Context retention settings
- Thinking mode settings
- Answer display mode preference
- Tool execution display preferences
- Performance metrics display preferences
- Human-in-the-Loop confirmation settings

**Example `~/.config/ollmcp/config.json`:**

```json
{
  "defaultProvider": "openai",
  "providers": {
    "ollama": { "host": "http://localhost:11434", "model": "qwen3:1.7b", "apiKey": "" },
    "openai": { "host": "", "model": "gpt-5.5", "apiKey": "sk-..." }
  },
  "enabledTools": {},
  "modelConfig": {},
  "...": "shared settings"
}
```

> [!TIP]
> Older flat config files (with top-level `host`/`model`/`provider`/`apiKey`) are migrated automatically the first time you run this version, and rewritten in the per-provider format on your next `/save-config`.

## Server Configuration Format

The JSON configuration file supports STDIO, SSE, and Streamable HTTP server types (MCP 1.10.1):

```json
{
  "mcpServers": {
    "stdio-server": {
      "command": "command-to-run",
      "args": ["arg1", "arg2", "..."],
      "env": {
        "ENV_VAR1": "value1",
        "ENV_VAR2": "value2"
      },
      "disabled": false
    },
    "sse-server": {
      "type": "sse",
      "url": "http://localhost:8000/sse",
      "headers": {
        "Authorization": "Bearer your-token-here"
      },
      "disabled": true
    },
    "http-server": {
      "type": "streamable_http",
      "url": "http://localhost:8000/mcp",
      "headers": {
        "X-API-Key": "your-api-key-here"
      },
      "disabled": false
    }
  }
}
```
> [!NOTE]
> **MCP 1.10.1 Transport Support**: The client now supports the latest Streamable HTTP transport with improved performance and reliability. If you specify a URL without a type, the client will default to using Streamable HTTP transport.

### Tips: where to put MCP server configs and a working example

A common point of confusion is where to store MCP server configuration files and how the TUI's save/load feature is used. Here's a short, practical guide that has helped other users:

- The TUI's `save-config` / `load-config` (or `sc` / `lc`) commands are intended to save *TUI preferences* like which tools you enabled, your selected model, thinking mode, display mode, and other client-side settings. They are not required to register MCP server connections with the client.
- For MCP server JSON files (the `mcpServers` object shown above) we recommend keeping them outside the TUI config directory or in a clear subfolder, for example:

```
~/.config/ollmcp/mcp-servers/config.json
```

You can then point `ollmcp` at that file at startup with `-j` / `--servers-json`.

> [!IMPORTANT]
> For HTTP-based MCP servers, `"type": "http"`, `"streamable-http"`, and `"streamable_http"` are all accepted and treated the same way. Also check the [Common MCP endpoint paths](#common-mcp-endpoint-paths) section below for typical endpoints.

Here a minimal working example let's say this is your `~/.config/ollmcp/mcp-servers/config.json`:

```json
{
  "mcpServers": {
    "github": {
      "type": "streamable_http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {
        "Authorization": "Bearer mytoken"
      }
    }
  }
}
```

> [!TIP]
> When using GitHub MCP server, make sure to replace `"mytoken"` with your actual GitHub API token.

With that file in place you can connect using:

```
ollmcp -j ~/.config/ollmcp/mcp-servers/config.json
```

Here you can find a GitHub issue related to this common pitfall: https://github.com/jonigl/mcp-client-for-ollama/issues/112#issuecomment-3446569030

#### Demo

A short demo (asciicast) that should help anyone reproduce the working setup quickly. This example uses an [MCP server example with streamable HTTP protocol](https://github.com/jonigl/mcp-server-with-streamable-http-example) usage:

[![asciicast](https://asciinema.org/a/751387.svg)](https://asciinema.org/a/751387)

#### Common MCP endpoint paths

Streamable HTTP MCP servers typically expose the MCP endpoint at `/mcp` (e.g., `https://host/mcp`), while SSE servers commonly use `/sse` (e.g., `https://host/sse`). Below is an excerpt from the MCP specification (2025-06-18):
> The server MUST provide a single HTTP endpoint path (hereafter referred to as the MCP endpoint) that supports both POST and GET methods. For example, this could be a URL like https://example.com/mcp.

You can find more details in the [MCP specification version 2025-06-18 - Transports](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports).

## Compatible Models

The following Ollama models work well with tool use:

- gemma4
- qwen3.5
- lfm2.5-thinking
- llama3.2
- mistral

For a complete list of Ollama models with tool use capabilities, visit the [official Ollama models page](https://ollama.com/search?c=tools).

For models that can also process images returned by tools, see the [Ollama vision models page](https://ollama.com/search?c=vision).

### Ollama Cloud Models

MCP Client for Ollama now supports [Ollama Cloud models](https://github.com/ollama/ollama/blob/main/docs/cloud.md), allowing you to use powerful cloud-hosted models with tool calling capabilities while leveraging your local MCP tools. Cloud models can run without a powerful local GPU, making it possible to access larger models that wouldn't fit on a personal computer.

**Supported Ollama Cloud models include for example:**
- `gpt-oss:20b-cloud`
- `gpt-oss:120b-cloud`
- `deepseek-v3.1:671b-cloud`
- `qwen3-coder:480b-cloud`

**To use Ollama Cloud models with this client:**

1. First, pull the cloud model:
   ```bash
   ollama pull gpt-oss:120b-cloud
   ```

2. Run the client with your chosen cloud model:
   ```bash
   ollmcp --model gpt-oss:120b-cloud
   ```

> [!NOTE]
> The model `deepseek-v3.1:671b-cloud` only supports tool use when thinking mode is turned off. You can toggle thinking mode in `ollmcp` by typing either `thinking-mode` or `tm`.

For more information about Ollama Cloud, visit the [Ollama Cloud documentation](https://docs.ollama.com/cloud).

### How Tool Calls Work

1. The client sends your query to Ollama with a list of available tools
2. If Ollama decides to use a tool, the client:
   - Displays the tool execution with formatted arguments and syntax highlighting
   - Shows a Human-in-the-Loop confirmation prompt (if enabled) allowing you to review and approve the tool call
   - Extracts the tool name and arguments from the model response
   - Calls the appropriate MCP server with these arguments (only if approved or HIL is disabled)
   - Shows the tool response in a structured, easy-to-read format (including image and unsupported-media summaries)
   - If the tool returned images and the current model supports vision, attaches the images to the next LLM message; otherwise displays a warning
   - Sends the tool result back to Ollama
   - If in Agent Mode, repeats the process if the model requests more tool calls
3. Finally, the client:
   - Displays the model's final response incorporating the tool results

### Agent Mode

Some models may request multiple tool calls in a single conversation. The client supports an **Agent Mode** that allows for iterative tool execution:
- When the model requests a tool call, the client executes it and sends the result back to the model
- This process repeats until the model provides a final answer or reaches the configured loop limit
- You can set the maximum number of iterations using the `loop-limit` (`ll`) command
- The default loop limit is `7` to prevent infinite loops

#### When the loop limit is reached

Instead of silently stopping, the client pauses and asks you how to proceed:

| Choice | Key | Description |
|--------|-----|-------------|
| **Continue** | `c` *(default)* | Grant another batch of iterations (same size as the current limit) |
| **Number** | `n` | Choose exactly how many more iterations to allow |
| **Unlimited** | `u` | Remove the cap and run until the model stops requesting tools |
| **Wrap up** | `w` | Ask the model to summarise what it gathered so far and produce a final answer — preserves all tool results collected before the limit |
| **Abort** | `a` | Discard the turn entirely (nothing saved to history) |

> [!NOTE]
> If you want to prevent using Agent Mode, simply set the loop limit to `1`.

#### Agent Mode Quick Demo:

[![asciicast](https://asciinema.org/a/476qpEamCX9TFQt4jNEXIgHxS.svg)](https://asciinema.org/a/476qpEamCX9TFQt4jNEXIgHxS)

## Where Can I Find More MCP Servers?

You can explore a collection of MCP servers in the official [MCP Servers repository](https://github.com/modelcontextprotocol/servers).

This repository contains reference implementations for the Model Context Protocol, community-built servers, and additional resources to enhance your LLM tool capabilities.

## Related Projects

- **[Ollama MCP Bridge](https://github.com/jonigl/ollama-mcp-bridge)** - A Python API layer that sits in front of Ollama, automatically adding tools from multiple MCP servers to every chat request. This project provides a transparent proxy solution that pre-loads all MCP servers at startup and seamlessly integrates their tools into the Ollama API.
- **[MCP Server with Streamable HTTP Example](https://github.com/jonigl/mcp-server-with-streamable-http-example)** - An example MCP server demonstrating the usage of the streamable HTTP protocol.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Ollama](https://ollama.com/) for the local LLM runtime
- [Model Context Protocol](https://modelcontextprotocol.io/) for the specification and examples
- [Rich](https://rich.readthedocs.io/) for the terminal user interface
- [Typer](https://typer.tiangolo.com/) for the modern CLI experience
- [Prompt Toolkit](https://python-prompt-toolkit.readthedocs.io/) for the interactive command line interface
- [UV](https://www.uvicorn.org/) for the lightning-fast Python package manager and virtual environment management
- [Asciinema](https://asciinema.org/) for the demo recording

---

Made with ❤️ by [jonigl](https://github.com/jonigl)
