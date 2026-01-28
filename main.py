import os
import discord
from discord.ext import commands
import ollama
import asyncio

# Bot configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
MODEL_NAME = "llama3.2:1b"

# Set up bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


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
            from datetime import datetime, timezone

            messages = [
                {
                    "role": "system",
                    "content": "You are chatbot in a discord community, but you are treated as a friend. Your name is llama. You care about the people in the chat. You are talking to multiple different users - pay attention to who said what, as different people may be having different conversations or topics. When responding, be aware of who you're replying to and what they specifically said. Each message includes a timestamp - use this to understand context like if someone is responding to an older message, if time has passed, or if conversations are happening quickly. Keep your responses concise and to the point. Aim for 2-3 sentences.",
                }
            ]

            # Fetch last 10 messages for context (excluding the current command)
            history = []
            async for message in ctx.channel.history(limit=11):
                if message.id != ctx.message.id:  # Skip the current command message
                    history.append(message)

            # Reverse to get chronological order (oldest first)
            history.reverse()

            # Add recent messages to context with timestamps
            for msg in history:
                # Format timestamp as HH:MM
                timestamp = msg.created_at.strftime("%H:%M")

                if msg.author.bot and msg.author.id == bot.user.id:
                    # Bot's previous responses
                    messages.append(
                        {"role": "assistant", "content": f"[{timestamp}] {msg.content}"}
                    )
                elif msg.content.startswith("!chat "):
                    # Include previous chat commands with the username for context
                    command_text = msg.content[6:]  # Remove "!chat " prefix
                    messages.append(
                        {
                            "role": "user",
                            "content": f"[{timestamp}] {msg.author.display_name}: {command_text}",
                        }
                    )
                elif not msg.content.startswith("!"):
                    # Regular user messages
                    messages.append(
                        {
                            "role": "user",
                            "content": f"[{timestamp}] {msg.author.display_name}: {msg.content}",
                        }
                    )

            # Add the current prompt with username and timestamp
            from datetime import datetime, timezone

            current_timestamp = ctx.message.created_at.strftime("%H:%M")
            messages.append(
                {
                    "role": "user",
                    "content": f"[{current_timestamp}] {ctx.author.display_name}: {prompt}",
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

            # Extract the response content
            reply = response["message"]["content"]

            # Discord has a 2000 character limit, so split if needed
            if len(reply) > 2000:
                chunks = [reply[i : i + 2000] for i in range(0, len(reply), 2000)]
                for chunk in chunks:
                    await ctx.send(chunk)
            else:
                await ctx.send(reply)

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

    print(f"Starting bot with model: {MODEL_NAME}")
    print(f"Ollama host: {OLLAMA_HOST}")
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
