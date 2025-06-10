<p align="center">

  <img src="https://github.com/jonigl/mcp-client-for-ollama/blob/main/misc/ollmcp-logo-512.png?raw=true" width="256" />
</p>
<p align="center">
<i>A simple yet powerful Python client for interacting with Model Context Protocol (MCP) servers using Ollama, allowing local LLMs to use tools.</i>
</p>

---
# ollmcp

`ollmcp` is a command-line interface for connecting to MCP servers using Ollama.

![ollmpc usage demo gif](https://raw.githubusercontent.com/jonigl/mcp-client-for-ollama/v0.2.5/misc/ollmcp-demo.gif)

## Installation

```
pip install ollmcp
```

## Usage

```
ollmcp [options]
```

## Description

This is a lightweight package that provides the `ollmcp` command-line interface. It's a convenience wrapper around the main [`mcp-client-for-ollama`](https://github.com/jonigl/mcp-client-for-ollama) package.

The actual implementation is contained in the main package. This package simply provides a more convenient and shorter name for installing the CLI tool.

## License

MIT
