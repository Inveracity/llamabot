FROM python:3.12-slim

WORKDIR /app

RUN pip install uv
COPY pyproject.toml .
RUN uv pip install --system -r pyproject.toml

COPY main.py .

# Run the bot with unbuffered output
CMD ["python", "-u", "main.py"]
