# ✨ Pexels AI CLI (`px` / `pexels-cli`)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Built with uv](https://img.shields.io/badge/built%20with-uv-purple.svg)](https://github.com/astral-sh/uv)

A modern, high-performance command-line tool for [Pexels](https://www.pexels.com/api/), designed for **Humans** (Rich visual UI) and **AI Agents / Classifiers** (Machine-readable `--json` & `--state` JSONL output).

---

## ⚡ Key Features

* 🤖 **Classifier-Ready JSONL Stream (`--state`)**: Stream compact candidate objects with generated `state` strings for non-generative decision models (Laya / System 1 classifiers):
  ```bash
  px videos --queries "black friday shopping,christmas shopping,checkout cart" \
    --per-page 8 --state --dedupe > candidates.jsonl
  ```
* 🎯 **Multi-Query Batch Execution (`--queries` & `--queries-file`)**: Execute multiple search queries in a single CLI call.
* 🧹 **Deduplication (`--dedupe`)**: Automatically deduplicate candidates by ID across multiple search queries.
* 🔍 **Field Filtering (`--fields`)**: Keep only specified keys (e.g. `--fields id,url,photographer,width,height`) to reduce payload noise.
* 🖼️ **Dedicated Photo Search (`px search` / `px photos`)**: Search stock photos with color hex codes, orientation, resolution, and localization filters.
* 🎥 **Dedicated Video Search (`px videos`)**: Search HD & 4K stock video footage with aspect ratio and quality filtering.
* 🧠 **Multi-Provider AI Engine**: Supports **Google Gemini** (`gemini-2.5-flash`), **OpenAI** (`gpt-4o-mini`), and **Ollama** (Local LLM `llama3.2`).
* ⚡ **High-Speed Downloader**: Async stream downloader with rich progress bars (`px download`).

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

## 🤖 Classifier Pipeline Integration (Laya / Decision Models)

Pipe candidate streams directly into typed-decision classification models:

```bash
px videos --queries "black friday shopping,online shopping,checkout cart" \
  --per-page 8 --state --dedupe > candidates.jsonl
```

### Output JSONL format (`candidates.jsonl`):
```json
{"id": 5890229, "type": "video", "query": "black friday shopping", "state": "a man shopping on black friday (photographer: Pavel Danilyuk)", "url": "https://www.pexels.com/video/a-man-shopping-on-black-friday-5890229/", "duration": 10, "width": 2160, "height": 3840}
```

---

## 📖 Usage Examples

### 1. Photo Search (Standard & AI)
```bash
# Standard Photo Search
px search "cyberpunk city" --color blue --orientation landscape

# Multi-query Photo Search with Field Filtering
px search --queries "mountains,forest,sunset" --fields id,url,photographer --json

# Smart AI Photo Search
px smart-photo "Dark moody tech background with subtle neon blue accents"
```

### 2. Video Search (Standard & AI)
```bash
# Standard Video Search
px videos "drone ocean waves" --orientation landscape

# Multi-query Video Search with State Generation
px videos --queries "city traffic,highway drone,night car" --state --dedupe

# Smart AI Video Search
px smart-video "Slow motion rainfall on city pavement"
```

### 3. Media Downloading
```bash
# Download photo by ID
px download 12377231 --output ./photo.jpg

# Download 4K video by ID
px download 25460961 --type video --output ./clip.mp4
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
