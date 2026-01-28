FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml .
COPY main.py .

# Install dependencies using uv
RUN uv pip install --system -r pyproject.toml

# Run the bot
CMD ["python", "main.py"]
