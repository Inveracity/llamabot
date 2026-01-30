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
MAX_CONTEXT_MESSAGES = 10

# Set up bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Store context clear markers per channel
context_cleared_at = {}


# Load system prompt from file
def load_system_prompt():
    """Load system prompt from markdown file"""
    try:
        prompt_path = Path(SYSTEM_PROMPT_FILE)
        return prompt_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        print(f"[WARNING] System prompt file not found: {SYSTEM_PROMPT_FILE}")
        return ""


def format_timestamp(dt):
    """Format datetime to HH:MM string"""
    return dt.strftime("%H:%M")


def format_message(timestamp, username, content):
    """Format message with timestamp and username"""
    return f"[{timestamp}] {username}: {content}"


async def fetch_channel_history(ctx, max_messages):
    """Fetch message history from channel, respecting clear marker"""
    history = []
    async for message in ctx.channel.history(limit=max_messages):
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
            # Initialize Ollama client
            client = ollama.Client(host=OLLAMA_HOST)

            # Build conversation with proper role assignment
            messages = []

            # Add system prompt to define bot personality
            system_prompt = load_system_prompt()
            messages.append({"role": "system", "content": system_prompt})

            history = await fetch_channel_history(ctx, MAX_CONTEXT_MESSAGES)

            for msg in history:
                if msg.author.bot and msg.author.id == bot.user.id:
                    messages.append({"role": "assistant", "content": msg.content})
                elif not msg.author.bot:
                    if msg.content.startswith("!chat "):
                        messages.append(
                            {"role": "user", "content": msg.content[len("!chat ") :]}
                        )
                # When there are 10 messages in total (system + 9), stop adding more
                if len(messages) >= MAX_CONTEXT_MESSAGES:
                    break

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

        except Exception as e:
            await ctx.send(f"Error: {str(e)}")
            print(f"Error in chat command: {e}")


@bot.command(name="info")
async def info(ctx):
    """Display information about the bot and model"""
    info_msg = (
        f"🤖 **Beardfist Llama Bot**\n"
        f"Model: {MODEL_NAME}\n"
        f"Ollama Host: {OLLAMA_HOST}\n"
        f"Commands:\n"
        f"  `!chat <message>` - Chat with the model\n"
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
