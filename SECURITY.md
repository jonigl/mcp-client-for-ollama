# Security

Security is a top priority; we appreciate responsible reporting.

## Reporting a vulnerability

Do **not** open a public issue. Instead:

1. Go to this repo’s **Security** tab
2. Click **Report a vulnerability**
3. Provide:

   * **A description of the vulnerability**
   * **Steps to reproduce the issue**
   * **Your assessment of the potential impact**
   * **Any possible mitigations**

## Trust model

`ollmcp` connects a language model to one or more MCP servers and lets the model
call their tools and read their resources. It is important to understand where
the trust boundaries are:

* **MCP servers you connect are trusted by you.** A server runs as a local
  process or a remote endpoint you explicitly added (`ollmcp mcp add ...`). Only
  connect servers you trust, the same way you would only run software you trust.
* **Tool and resource responses are treated as untrusted content.** Whatever a
  server returns is passed into the model's context so the model can use it. A
  malicious or compromised server can embed instructions inside its responses
  (this is known as **indirect prompt injection**) in an attempt to make the
  model call other tools you did not intend.

This is an inherent property of the MCP / tool-use paradigm, not a bug specific
to this client: for a tool to be useful, its output must reach the model, and
there is no reliable way to distinguish "data" from "instructions" in free-form
text. The right defense is **not** to connect untrusted servers, combined with
the defense-in-depth measures below.

## How this client helps you stay in control

* **Human-in-the-Loop (HIL) confirmation is enabled by default.** Before any
  tool runs, you are shown the tool name and its **full arguments** (values are
  never truncated, terminal control characters are stripped, and Rich markup is
  escaped) so you can review exactly what would execute before approving.
* **You choose which tools are enabled** per server, and can disable any tool.
* **Agent Mode is bounded** by a configurable iteration limit.

Because tool responses are untrusted, keep HIL enabled when you use servers that
can take consequential actions (filesystem writes, shell execution, network
requests, browser automation), and read the arguments before confirming.

## Security recommendations

* Keep the client up to date
* Only connect MCP servers you trust, and keep HIL enabled for powerful tools
* Run with only the necessary permissions (least privilege)
* Review tool arguments in the confirmation prompt before approving

## Acknowledgments

Thanks to the people who have responsibly reported security issues or suggested
hardening improvements to this project:

* [@fortress07](https://github.com/fortress07) — reported that the
  Human-in-the-Loop confirmation truncated tool arguments, which led to the
  confirmation display being hardened to show arguments in full and to strip
  terminal control characters.

Thank you for helping keep this project secure.
