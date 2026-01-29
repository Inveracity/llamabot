# Copilot Instructions for Beardfist Llama Discord Bot

## Project Overview

This is a Discord bot that integrates with Ollama to provide LLM chat capabilities using Llama 3.2:1b model. The bot runs in Docker Compose with two services: an Ollama server and the Discord bot client.

## Tech Stack

- **Language**: Python 3.12+
- **Framework**: discord.py 2.6.4+
- **LLM**: Ollama (llama3.2:1b model)
- **Containerization**: Docker & Docker Compose
- **Dependency Management**: uv (pyproject.toml)

## Architecture

### Services
1. **ollama-small**: Ollama server running on port 11435
2. **llama-bot**: Discord bot that communicates with Ollama

### Key Components
- `main.py`: Main bot logic with Discord commands
- `system_prompt.md`: System prompt configuration for bot personality
- `docker-compose.yml`: Service orchestration
- `Dockerfile`: Bot container image
- `ollama-entrypoint.sh`: Ollama service initialization

## Code Style Guidelines

### Python Conventions
- Use async/await for all Discord operations
- Type hints encouraged but not currently enforced
- Keep functions focused and single-purpose
- Use descriptive variable names (e.g., `ctx`, `prompt`, `messages`)
- **Always run `uv run ruff check --fix` after making code changes** to catch linting issues and auto-fix formatting
- Run `uv run ruff check` without `--fix` to preview issues before applying fixes

### Discord.py Patterns
- Use `@bot.command()` decorator for commands
- Always use `async with ctx.typing()` for long operations
- Handle Discord's 2000 character message limit
- Provide error messages to users on failures

### Ollama Integration
- Initialize client per request: `ollama.Client(host=OLLAMA_HOST)`
- Use conversation history format: `[{"role": "system|user|assistant", "content": "..."}]`
- System prompt loaded from `system_prompt.md` file via `load_system_prompt()` function
- Limit token generation with `num_predict` option

## Bot Behavior

### Conversation Context
- Fetches last 10 messages from channel history for context
- Includes timestamps in format `[HH:MM]` for temporal awareness
- Preserves username with each message for multi-user conversations
- Excludes bot commands that don't use `!chat`
- Bot sees itself as "llama" and acts as a friend in the community

### System Prompt
- Stored in `system_prompt.md` file
- Loaded at runtime via `SYSTEM_PROMPT_FILE` environment variable (defaults to `/app/system_prompt.md`)
- Defines bot as "llama", a friendly member of the Beardfist community
- Principles: concise responses (2-3 sentences), context-aware, friendly and helpful
- Can be edited without modifying code - changes take effect on bot restart

## Common Tasks

### Adding New Commands
```python
@bot.command(name="commandname")
async def commandname(ctx, *, arg: str):
    """Command description"""
    async with ctx.typing():
        try:
            # Command logic here
            await ctx.send("Response")
        except Exception as e:
            await ctx.send(f"Error: {str(e)}")
```

After adding or modifying code:
```bash
uv run ruff check --fix
```

### Modifying Ollama Parameters
Edit the `options` dict in the `client.chat()` call:
- `temperature`: 0.0-1.0 (creativity level)
- `num_predict`: Max tokens to generate
- `top_p`, `top_k`: Sampling parameters

### Changing Model
Update `MODEL_NAME` constant and pull new model:
```bash
docker exec ollama-small ollama pull <model-name>
```

## Environment Variables

Required:
- `DISCORD_TOKEN`: Discord bot authentication token

Optional:
- `OLLAMA_HOST`: Defaults to `http://ollama:11434` (internal Docker network)

## Docker Operations

### Starting Services
```bash
docker compose up -d
```

### Viewing Logs
```bash
docker compose logs -f llama-bot
docker compose logs -f ollama-small
```

### Rebuilding Bot
```bash
docker compose up -d --build llama-bot
```

### Accessing Ollama CLI
```bash
docker compose exec ollama-small bash
ollama list
ollama pull <model>
```

## Testing Considerations

- Test in a private Discord server first
- Verify conversation history tracking with multiple users
- Check response length handling (2000 char limit)
- Test error handling for Ollama connection issues
- Verify timestamp formatting across timezones

## Performance Notes

- Ollama configured for minimal resource usage:
  - `OLLAMA_NUM_PARALLEL=1`
  - `OLLAMA_MAX_LOADED_MODELS=1`
  - `OLLAMA_MAX_QUEUE=1`
- 1B model chosen for speed over quality
- Response tokens limited to 150 for faster generation
- Consider upgrading model size if hardware allows

## Future Enhancement Ideas

- Add conversation memory persistence
- Implement user-specific context
- Add model selection command
- Include image analysis capabilities (multimodal models)
- Rate limiting per user
- Admin commands for model management
- Streaming responses for longer generations

## Troubleshooting

### Bot not responding
1. Check bot has message content intent enabled
2. Verify Discord token is valid
3. Check bot has permissions in channel
4. Review logs: `docker compose logs llama-bot`

### Ollama connection errors
1. Verify ollama-small is healthy: `docker compose ps`
2. Check network connectivity between containers
3. Ensure model is pulled: `docker exec ollama-small ollama list`

### Memory issues
1. Reduce conversation history limit
2. Switch to smaller model
3. Reduce `num_predict` value
4. Check Docker resource limits

## Security Notes

- Never commit `.env` file with Discord token
- Use `.env.example` as template
- Discord token grants full bot access - keep secure
- Bot can see all messages in channels it has access to
- Consider implementing command permissions if needed
