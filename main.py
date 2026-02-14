import os
import signal
import sys
import asyncio
from pathlib import Path
import discord
from discord.ext import commands
import ollama

# Bot configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.2:1b")
SYSTEM_PROMPT_FILE = os.getenv("SYSTEM_PROMPT_FILE", "/app/system_prompt.md")

# Ollama generation parameters
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.9))
NUM_PREDICT = int(os.getenv("LLM_NUM_PREDICT", 150))
TOP_P = float(os.getenv("LLM_TOP_P", 0.95))
REPEAT_PENALTY = float(os.getenv("LLM_REPEAT_PENALTY", 1.1))

# Chat context
MAX_CONTEXT_MESSAGES = 4
MAX_HISTORY_MESSAGES = 50

# Set up bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# The context delimiter filters out any prior messages, ie. !chat -- <message>
CONTEXT_DELIMITER = "--"


# Load system prompt from file
def load_system_prompt(prompt_file=None):
    """Load system prompt from markdown file"""
    try:
        if prompt_file is None:
            prompt_file = SYSTEM_PROMPT_FILE
        prompt_path = Path(prompt_file)
        return prompt_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        print(f"[WARNING] System prompt file not found: {prompt_file}")
        return ""


def format_timestamp(dt):
    """Format datetime to HH:MM string"""
    return dt.strftime("%H:%M")


def format_message(timestamp, username, content):
    """Format message with timestamp and username"""
    return f"[{timestamp}] {username}: {content}"


async def fetch_channel_history(ctx, max_history_messages):
    """Fetch message history from channel, respecting clear marker"""
    history = []
    async for message in ctx.channel.history(limit=max_history_messages):
        if message.id != ctx.message.id:
            history.append(message)

    # Reverse to chronological order
    history.reverse()
    return history


async def send_long_message(ctx, message):
    """Send message to Discord, splitting if it exceeds 2000 characters"""
    if len(message) > 2000:
        chunks = [message[i : i + 2000] for i in range(0, len(message), 2000)]
        for chunk in chunks:
            await ctx.send(chunk)
    else:
        await ctx.send(message)


async def chat_with_llm(ctx, prompt, command_name="chat", prompt_file=None):
    """Core chat functionality that can be used by different commands

    Args:
        ctx: Discord context
        prompt: User's message
        command_name: Command prefix ("chat" or "chad")
        prompt_file: Path to system prompt file (defaults to SYSTEM_PROMPT_FILE)
    """
    # Initialize Ollama client
    client = ollama.Client(host=OLLAMA_HOST)

    # prompts starting with "--" should not load any history
    skip_history = False
    if prompt.startswith(CONTEXT_DELIMITER):
        print("[DEBUG] Skipping history for this prompt")
        skip_history = True
        prompt = prompt[len(CONTEXT_DELIMITER) :].strip()

    messages = []

    if not skip_history:
        # Build conversation with proper role assignment
        history = await fetch_channel_history(ctx, MAX_HISTORY_MESSAGES)

        for msg in history:
            # Reset context if we encounter a delimiter-marked message
            if not msg.author.bot and msg.content.startswith(
                f"!{command_name} {CONTEXT_DELIMITER}"
            ):
                print(
                    f"[DEBUG] Found delimiter at message {msg.id}, clearing prior history"
                )
                messages.clear()
                # Include the delimiter message itself (without the delimiter)
                messages.append(
                    {
                        "role": "user",
                        "content": msg.content[
                            len(f"!{command_name} {CONTEXT_DELIMITER}") :
                        ].strip(),
                    }
                )
                continue

            if msg.author.bot and msg.author.id == bot.user.id:
                messages.append({"role": "assistant", "content": msg.content})
            elif not msg.author.bot:
                if msg.content.startswith(f"!{command_name} "):
                    messages.append(
                        {
                            "role": "user",
                            "content": msg.content[len(f"!{command_name} ") :],
                        }
                    )

        # Keep only the most recent messages
        if len(messages) >= MAX_CONTEXT_MESSAGES:
            messages = messages[-MAX_CONTEXT_MESSAGES:]

    # Inject system prompt at the beginning
    system_prompt = load_system_prompt(prompt_file)
    messages.insert(0, {"role": "system", "content": system_prompt})

    # Add the current user prompt
    messages.append({"role": "user", "content": prompt})

    for msg in messages:
        print(f"[DEBUG] Message Role: {msg['role']}, Content: {msg['content']}")

    # Generate response (run blocking call in executor)
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.chat(
            model=MODEL_NAME,
            messages=messages,
            options={
                "temperature": TEMPERATURE,
                "num_predict": NUM_PREDICT,
                "top_p": TOP_P,
                "repeat_penalty": REPEAT_PENALTY,
            },
        ),
    )

    # Extract the response content and send it
    reply = response["message"]["content"]
    print(f"[DEBUG] Model reply: {reply}")
    await send_long_message(ctx, reply)


@bot.event
async def on_ready():
    """Event handler for when bot is ready"""
    print(f"{bot.user} has connected to Discord!")
    print(f"Connected to {len(bot.guilds)} guild(s)")


@bot.command(name="chat")
async def chat(ctx, *, prompt: str):
    """
    Chat with the Llama model
    Usage: !chat <your message>
    """
    async with ctx.typing():
        try:
            await chat_with_llm(ctx, prompt, command_name="chat")
        except Exception as e:
            await ctx.send(f"Error: {str(e)}")
            print(f"Error in chat command: {e}")


@bot.command(name="chad")
async def chad(ctx, *, prompt: str):
    """
    Chat with the Llama model in Chad mode (more humorous responses)
    Usage: !chad <your message>
    """
    async with ctx.typing():
        try:
            await chat_with_llm(
                ctx, prompt, command_name="chad", prompt_file="/app/chad_prompt.md"
            )
        except Exception as e:
            await ctx.send(f"Error: {str(e)}")
            print(f"Error in chad command: {e}")


@bot.command(name="info")
async def info(ctx):
    """Display information about the bot and model"""
    info_msg = (
        f"**Llama Bot**\n"
        f"Model: {MODEL_NAME}\n"
        f"Ollama Host: {OLLAMA_HOST}\n"
        f"Commands:\n"
        f"  `!chat <message>` - Chat with the model\n"
        f"  `!chad <message>` - Chat in Chad mode (more humorous)\n"
        f"  `!info` - Display this information"
    )
    await ctx.send(info_msg)


def main():
    """Main entry point for the bot"""
    if not DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN environment variable not set!")

    def signal_handler(sig, frame):
        """Handle SIGTERM and SIGINT for graceful shutdown"""
        print(f"\nReceived signal {sig}, shutting down gracefully...")
        sys.exit(0)

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    print(f"Starting bot with model: {MODEL_NAME}")
    print(f"Ollama host: {OLLAMA_HOST}")

    try:
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("Bot stopped by user")
    finally:
        print("Bot shutdown complete")


if __name__ == "__main__":
    main()
