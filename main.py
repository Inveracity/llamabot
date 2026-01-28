import os
import signal
import sys
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

            # Build conversation history from recent messages

            messages = [
                {
                    "role": "system",
                    "content": "You are chatbot in a discord community, but you are treated as a friend. Your name is llama. You care about the people in the chat. You are talking to multiple different users - pay attention to who said what, as different people may be having different conversations or topics. When responding, be aware of who you're replying to and what they specifically said. Each message includes a timestamp - use this to understand context like if someone is responding to an older message, if time has passed, or if conversations are happening quickly. Keep your responses concise and to the point. Aim for 2-3 sentences.",
                }
            ]

            # Fetch last 10 messages for context (excluding the current command)
            history = []
            clear_marker = context_cleared_at.get(ctx.channel.id)
            async for message in ctx.channel.history(limit=30):
                if message.id != ctx.message.id:  # Skip the current command message
                    # Stop if we hit the clear marker
                    if clear_marker and message.id == clear_marker:
                        break
                    history.append(message)

            # Reverse to get chronological order (oldest first)
            history.reverse()

            # Add recent messages to context with timestamps
            for msg in history:
                timestamp = format_timestamp(msg.created_at)

                if msg.author.bot and msg.author.id == bot.user.id:
                    # Bot's previous responses
                    messages.append(
                        {"role": "assistant", "content": f"[{timestamp}] {msg.content}"}
                    )
                elif msg.content.startswith("!chat ") or not msg.content.startswith(
                    "!"
                ):
                    # User messages (both chat commands and regular messages)
                    content = (
                        msg.content[6:]
                        if msg.content.startswith("!chat ")
                        else msg.content
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": format_message(
                                timestamp, msg.author.display_name, content
                            ),
                        }
                    )

            # Add the current prompt with username and timestamp
            current_timestamp = format_timestamp(ctx.message.created_at)
            messages.append(
                {
                    "role": "user",
                    "content": format_message(
                        current_timestamp, ctx.author.display_name, prompt
                    ),
                }
            )

            # Generate response with conversation context
            response = client.chat(
                model=MODEL_NAME,
                messages=messages,
                options={
                    "temperature": 0.7,
                    "num_predict": 150,  # Limit response to ~150 tokens
                },
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
