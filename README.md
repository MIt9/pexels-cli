# ✨ Pexels AI CLI (`px` / `pexels-cli`)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Built with uv](https://img.shields.io/badge/built%20with-uv-purple.svg)](https://github.com/astral-sh/uv)

A modern, high-performance command-line tool for [Pexels](https://www.pexels.com/api/), designed for **Humans** (Rich visual UI) and **AI Agents** (Machine-readable `--json` output).

---

## ⚡ Key Features

* 🖼️ **Dedicated Photo Search (`px search` / `px photos`)**: Search stock photos with color hex codes, orientation, resolution, and localization filters.
* 🎥 **Dedicated Video Search (`px videos`)**: Search HD & 4K stock video footage with aspect ratio and quality filtering.
* 🤖 **Dedicated AI Smart Search**:
  * `px smart-photo`: AI natural language photo search (color palette inference, composition tags).
  * `px smart-video`: AI natural language video search (motion, resolution, and framing tags).
* 🧠 **Multi-Provider AI Engine**: Supports **Google Gemini** (`gemini-2.5-flash`), **OpenAI** (`gpt-4o-mini`), and **Ollama** (Local LLM `llama3.2`).
* 🤖 **AI-Agent Friendly (`--json`)**: Every command supports `--json` or global `PX_OUTPUT_FORMAT=json` for clean, zero-ANSI JSON output designed for AI subagents, shell automation, and pipelines.
* ⚡ **High-Speed Downloader**: Async stream downloader with rich progress bars (`px download`).
* 🎨 **Enhanced Prompting & Curation**:
  * `px ai enhance`: Expands search concepts into stock photography keywords & aesthetic styles.
  * `px ai curate`: Generates structured stock media shot lists based on project briefs.

---

## 🚀 Global Installation

### Option 1: Install globally via `uv` (Recommended)

```bash
uv tool install pexels-ai-cli
```

### Option 2: Install via `pip` / `pipx`

```bash
pipx install pexels-ai-cli
```

---

## 🔑 Quick Setup & Configuration

### 1. Set Pexels API Key
Get your free API key at [Pexels API Portal](https://www.pexels.com/api/).
```bash
px config set-pexels-key YOUR_PEXELS_API_KEY
```

### 2. Set AI Key (Optional)
```bash
# Set Gemini Key (Default Provider)
px config set-ai-key YOUR_GEMINI_API_KEY --provider gemini

# Or OpenAI
px config set-ai-key YOUR_OPENAI_API_KEY --provider openai

# Or Ollama (Local LLM, no API key needed)
px config set-ai-key http://localhost:11434 --provider ollama --model llama3.2
```

---

## 📖 Usage Examples

### Photo Search (Standard & AI)
```bash
# Standard Photo Search
px search "cyberpunk city" --color blue --orientation landscape

# Smart AI Photo Search
px smart-photo "Dark moody tech background with subtle neon blue accents"
```

### Video Search (Standard & AI)
```bash
# Standard Video Search
px videos "drone ocean waves" --orientation landscape

# Smart AI Video Search
px smart-video "Slow motion rainfall on city pavement"
```

### Media Downloading
```bash
# Download photo by ID
px download 12377231 --output ./photo.jpg

# Download 4K video by ID
px download 25460961 --type video --output ./clip.mp4
```

### Scripting for AI Subagents (`--json`)
```bash
px search "mountains" --json
px smart-photo "cozy autumn coffee" --json
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
