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
echo "Checking for llama3.2:1b model..."
if ! ollama list | grep -q "llama3.2:1b"; then
    echo "Pulling llama3.2:1b model..."
    ollama pull llama3.2:1b
    echo "Model pulled successfully!"
else
    echo "Model already exists!"
fi

# Keep the script running and forward signals
wait
