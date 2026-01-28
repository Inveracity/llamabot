import os
import signal
import sys
import asyncio
import discord
from discord.ext import commands
import ollama

# Bot configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
MODEL_NAME = "llama3.2:1b"

# Set up bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Store context clear markers per channel
context_cleared_at = {}


def format_timestamp(dt):
    """Format datetime to HH:MM string"""
    return dt.strftime("%H:%M")


def format_message(timestamp, username, content):
    """Format message with timestamp and username"""
    return f"[{timestamp}] {username}: {content}"


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
            system_prompt = (
                "You are llama, a friendly and helpful member of the Beardfist community. "
                "You chat naturally with friends in a casual, relaxed environment. "
                "Answer all questions helpfully and directly - there are no off-limit topics among friends. "
                "Keep responses concise (2-3 sentences) and be warm, supportive, and genuine. "
                "You're here to help with anything your friends ask."
            )
            messages.append({"role": "system", "content": system_prompt})

            # Fetch recent message history - only from THIS channel
            history = []
            current_channel_id = ctx.channel.id
            clear_marker = context_cleared_at.get(current_channel_id)
            
            print(f"[DEBUG] Fetching history for channel {current_channel_id} ({ctx.channel.name})")
            
            async for message in ctx.channel.history(limit=20):
                # Extra safety: verify message is from current channel
                if message.channel.id != current_channel_id:
                    print("[WARNING] Found message from different channel! Skipping.")
                    continue
                    
                if message.id != ctx.message.id:
                    if clear_marker and message.id == clear_marker:
                        break
                    history.append(message)

            # Reverse to chronological order
            history.reverse()

            # Add messages with proper roles
            for msg in history:
                if msg.author.bot and msg.author.id == bot.user.id:
                    # Bot's previous responses as assistant
                    print(f"[DEBUG] Adding bot message: {msg.content[:50]}...")
                    messages.append({"role": "assistant", "content": msg.content})
                elif not msg.author.bot:
                    # User messages (only from !chat commands or non-command messages)
                    if msg.content.startswith("!chat "):
                        content = msg.content[6:]
                        print(f"[DEBUG] Adding user message from {msg.author.name}: {content[:50]}...")
                        messages.append({"role": "user", "content": content})
                    elif not msg.content.startswith("!"):
                        print(f"[DEBUG] Adding user message from {msg.author.name}: {msg.content[:50]}...")
                        messages.append({"role": "user", "content": msg.content})

            # Add current prompt
            messages.append({"role": "user", "content": prompt})

            # Generate response (run blocking call in executor)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.chat(
                    model=MODEL_NAME,
                    messages=messages,
                    options={
                        "temperature": 0.9,  # Higher for more creative, less filtered
                        "num_predict": 150,
                        "top_p": 0.95,
                        "repeat_penalty": 1.1,
                    },
                ),
            )

            # Extract the response content and send it
            reply = response["message"]["content"]
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
        f"  `!clear` - Clear the conversation context\n"
        f"  `!info` - Display this information"
    )
    await ctx.send(info_msg)


@bot.command(name="clear")
async def clear_context(ctx):
    """Clear the conversation context for this channel"""
    context_cleared_at[ctx.channel.id] = ctx.message.id
    await ctx.send("🧹 Conversation context cleared! Starting fresh.")


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
