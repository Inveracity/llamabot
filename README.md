# Beardfist Llama Discord Bot

A Discord bot powered by Llama 3.2 (1B) using Ollama, running in Docker Compose.

## Features

- Chat with Llama 3.2:1b model directly from Discord
- Containerized with Docker Compose
- Automatic model management with Ollama

## Prerequisites

- Docker and Docker Compose
- Discord Bot Token ([Create one here](https://discord.com/developers/applications))

## Setup

1. **Clone the repository** (if not already done)

2. **Configure Discord Token**
   ```bash
   cp .env.example .env
   # Edit .env and add your Discord bot token
   ```

3. **Start the services**
   ```bash
   docker-compose up -d
   ```

4. **Pull the Llama model** (first time only)
   ```bash
   docker exec ollama ollama pull llama3.2:1b
   ```

5. **Check logs**
   ```bash
   docker-compose logs -f bot
   ```

## Usage

In Discord, use the following commands:

- `!chat <message>` - Chat with the Llama model
- `!info` - Display bot information

Example:
```
!chat What is the meaning of life?
```

## Project Structure

- `main.py` - Discord bot implementation
- `docker-compose.yml` - Multi-container setup (Ollama + Bot)
- `Dockerfile` - Bot container configuration
- `pyproject.toml` - Python dependencies

## Services

- **ollama**: Runs the Ollama service with the Llama model
- **bot**: Discord bot that connects to Ollama

## Development

To run locally without Docker:

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Ensure Ollama is running and has the model:
   ```bash
   ollama pull llama3.2:1b
   ```

3. Set environment variables:
   ```bash
   export DISCORD_TOKEN=your_token_here
   export OLLAMA_HOST=http://localhost:11434
   ```

4. Run the bot:
   ```bash
   python main.py
   ```

## Troubleshooting

- **Bot not responding**: Check logs with `docker-compose logs bot`
- **Model not found**: Run `docker exec ollama ollama pull llama3.2:1b`
- **Connection issues**: Ensure Ollama service is healthy with `docker-compose ps`
