#!/bin/bash

# PCIe Visualization Tool Docker Runner
# This script builds and runs the PCIe visualization tool in a Docker container

# Set variables
IMAGE_NAME="pcie-visualization-tool"
CONTAINER_NAME="pcie-visualization"
PORT=7860

# Print banner
echo "====================================="
echo "PCIe Visualization Tool Docker Runner"
echo "====================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Detect architecture
ARCH=$(uname -m)
echo "Detected architecture: $ARCH"

# Build the Docker image with platform flag if needed
echo "Building Docker image..."
if [ "$ARCH" = "arm64" ]; then
    echo "Building for Apple Silicon (arm64)..."
    docker build --platform linux/arm64 -t $IMAGE_NAME .
else
    docker build -t $IMAGE_NAME .
fi

# Check if the build was successful
if [ $? -ne 0 ]; then
    echo "Error: Docker build failed."
    echo "Trying alternative build approach..."
    # Try with explicit platform
    docker build --platform linux/amd64 -t $IMAGE_NAME .
    
    if [ $? -ne 0 ]; then
        echo "Error: All Docker build attempts failed."
        exit 1
    fi
fi

# Check if a container with the same name is already running
if docker ps -a | grep -q $CONTAINER_NAME; then
    echo "Removing existing container..."
    docker rm -f $CONTAINER_NAME
fi

# Run the Docker container
echo "Starting container..."
docker run --name $CONTAINER_NAME -p $PORT:7860 -d $IMAGE_NAME

# Check if the container started successfully
if [ $? -ne 0 ]; then
    echo "Error: Failed to start Docker container."
    exit 1
fi

# Print success message and URL
echo "====================================="
echo "PCIe Visualization Tool is running!"
echo "Access the web interface at: http://localhost:$PORT"
echo "====================================="
echo "To stop the container, run: docker stop $CONTAINER_NAME"
echo "To view logs, run: docker logs $CONTAINER_NAME"
