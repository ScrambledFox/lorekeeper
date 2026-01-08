FROM python:3.11-slim

WORKDIR /app

# Install UV
RUN pip install uv

# Copy all project files needed for build
COPY pyproject.toml uv.lock* README.md ./
COPY lorekeeper ./lorekeeper

# Create virtual environment and install dependencies
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install -e .

EXPOSE 8000

CMD ["uvicorn", "lorekeeper.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
