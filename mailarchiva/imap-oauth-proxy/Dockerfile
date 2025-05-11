
# Use a Python image based on Alpine Linux
FROM python:3.11-alpine

# Set the working directory
WORKDIR /app


# Install core dependencies
RUN pip install --no-cache-dir emailproxy
# Copy the shell script into the container
COPY run_email_proxy.sh /app/

# Make the shell script executable
RUN chmod +x /app/run_email_proxy.sh

# Run the shell script
CMD ["/bin/sh", "/app/run_email_proxy.sh"]
