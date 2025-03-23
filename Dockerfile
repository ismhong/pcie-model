FROM python:3.9-slim

WORKDIR /app

# Copy the application code
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir gradio numpy pandas plotly

# Expose the Gradio web server port
EXPOSE 7860

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the Gradio app
CMD ["python", "pcie_gradio_ui.py"]
