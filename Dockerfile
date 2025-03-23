FROM python:3.9-slim

WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir gradio numpy pandas plotly

# Expose the Gradio web server port
EXPOSE 7860

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Copy the application code
COPY . /app/

# Run the Gradio app
CMD ["python", "pcie_bw_gradio_ui.py"]
