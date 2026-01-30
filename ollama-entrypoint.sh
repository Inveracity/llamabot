#!/bin/bash

# Start Ollama in the background
/bin/ollama serve &

# Wait for Ollama to be ready
echo "Waiting for Ollama service to be ready..."
while ! ollama list > /dev/null 2>&1; do
    sleep 1
done

echo "Ollama service is ready!"

# Pull the model if not already present
MODEL_NAME=${MODEL_NAME:-llama3.2:1b}
echo "Checking for $MODEL_NAME model..."
if ! ollama list | grep -q "$MODEL_NAME"; then
    echo "Pulling $MODEL_NAME model..."
    ollama pull $MODEL_NAME
    echo "Model pulled successfully!"
else
    echo "Model already exists!"
fi

# Keep the script running and forward signals
wait
