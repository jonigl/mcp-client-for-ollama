# Release Notes - External System Prompt Support

## Version 0.27.0

### 🎉 New Features

#### External System Prompt Files
We've added support for external system prompt files, allowing you to maintain multiple system prompts as `.md` files and quickly switch between them using keyboard shortcuts or commands.

### ✨ Key Features

1. **TAB/Shift+TAB Cycling**
   - Press `TAB` to cycle to the next system prompt
   - Press `Shift+TAB` to cycle to the previous system prompt
   - Active prompt is displayed in real-time in the prompt line

2. **Default Prompt Creation**
   - On first run, `default.md` is automatically created in `~/.config/ollmcp/system_prompts/`
   - Contains your current system prompt configuration
   - Set as the active prompt by default

3. **External File Priority**
   - External system prompt files override the manual system prompt set via `model-config`
   - This allows quick context switching without modifying model configuration

4. **Prompt Display**
   - Active prompt name is shown in the prompt line
   - Example: `qwen2.5/thinking/3-tools/default❯`

5. **Persistence**
   - Active system prompt is saved with your configuration
   - Automatically restored when loading a saved configuration

### 🚀 How to Use

#### 1. Creating Custom System Prompts

Create `.md` files in the system prompts directory:

```bash
# Create the directory if it doesn't exist
mkdir -p ~/.config/ollmcp/system_prompts/

# Create a planning prompt
cat > ~/.config/ollmcp/system_prompts/plan.md << 'EOF'
# Planning Mode

You are a planning assistant. Help users break down complex tasks into 
manageable steps and create structured plans for their projects.
EOF

# Create a coding prompt
cat > ~/.config/ollmcp/system_prompts/code.md << 'EOF'
# Coding Mode

You are an expert programmer. Provide clean, well-documented code with 
best practices and explain your reasoning.
EOF

# Create a review prompt
cat > ~/.config/ollmcp/system_prompts/review.md << 'EOF'
# Review Mode

You are a code reviewer. Analyze code for bugs, security issues, and 
improvements. Be thorough but constructive.
EOF
```

#### 2. Quick Switching with Keyboard

- **TAB**: Press to cycle to the next system prompt
  ```
  qwen2.5/thinking/3-tools/default❯ [Press TAB]
  → Active system prompt: plan
  qwen2.5/thinking/3-tools/plan❯
  ```

- **Shift+TAB**: Press to cycle to the previous system prompt
  ```
  qwen2.5/thinking/3-tools/plan❯ [Press Shift+TAB]
  → Active system prompt: default
  qwen2.5/thinking/3-tools/default❯
  ```

#### 3. Using Commands

**List Available Prompts:**
```
lp
# or
list-prompts
```

Output:
```
┌─ System Prompts ────────────────────────────────┐
│ ▶ default.md                                    │
│   plan.md                                       │
│   code.md                                       │
│   review.md                                     │
│                                                 │
│ Active prompt shown with ▶                      │
└─────────────────────────────────────────────────┘
```

**Select a Prompt Interactively:**
```
sp
# or
system-prompts
```

This will display available prompts and prompt you to enter a name:
```
┌─ System Prompts ────────────────────────────────┐
│ ▶ default.md                                    │
│   plan.md                                       │
│   code.md                                       │
└─────────────────────────────────────────────────┘
Config name (or press Enter for default)❯ code
Active system prompt set to: code
```

**Disable External System Prompt:**
```
sp
# then type: none
```

#### 4. Configuration Persistence

The active system prompt is automatically saved when you use `save-config`:

```
sc
# or
save-config
```

And restored when you use `load-config`:

```
lc
# or
load-config
```

### 📁 Directory Structure

```
~/.config/ollmcp/
├── config.json              # Main configuration
├── default.json            # Default configuration
└── system_prompts/         # System prompt files
    ├── default.md         # Default prompt (auto-created)
    ├── plan.md           # Custom planning prompt
    ├── code.md           # Custom coding prompt
    └── review.md         # Custom review prompt
```

### 🔧 Configuration Format

System prompt settings are stored in your configuration:

```json
{
  "systemPromptSettings": {
    "activePrompt": "plan"
  }
}
```

### ⚠️ Important Notes

1. **Priority**: External system prompt files take precedence over the manual system prompt set via `model-config`. If you want to use the manual system prompt, disable the external prompt by selecting "none".

2. **File Format**: Only `.md` files are loaded from the system prompts directory. The file extension is removed for the prompt name (e.g., `plan.md` becomes `plan`).

3. **Default Prompt**: The `default.md` file is created automatically on startup if it doesn't exist. It contains your current system prompt configuration at the time of creation.

4. **TAB Key Behavior**: The TAB key now cycles through system prompts instead of triggering completion when no text is entered. Use the command names directly or type `/` for prompt completion as before.

### 📝 Example Workflow

```bash
# Start the client
ollmcp

# The prompt shows the active system prompt:
# qwen2.5/thinking/3-tools/default❯

# Switch to planning mode
[Press TAB]
# → Active system prompt: plan
# qwen2.5/thinking/3-tools/plan❯

# Ask for help with a project
"Help me plan a new web application"

# Switch to coding mode
[Press TAB]
# → Active system prompt: code
# qwen2.5/thinking/3-tools/code❯

# Ask for code
"Write a Python function to parse JSON"

# Save the configuration with the active prompt
save-config

# Next time you load the config, 'code' will be the active prompt
```

### 🐛 Bug Fixes

- None in this release

### 📚 Documentation

- Updated help text with new system prompt commands
- Added comprehensive test suite (`tests/test_system_prompt_manager.py`)

### 🔗 Related Files

- `mcp_client_for_ollama/prompts/system_prompt_manager.py` - New module for managing system prompts
- `mcp_client_for_ollama/client.py` - Updated with keyboard bindings and commands
- `mcp_client_for_ollama/config/defaults.py` - Updated default configuration
- `mcp_client_for_ollama/config/manager.py` - Updated configuration validation
- `tests/test_system_prompt_manager.py` - New test suite

---

**Full Changelog**: Compare with previous version for detailed code changes.
