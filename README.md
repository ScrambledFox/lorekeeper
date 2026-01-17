# LoreKeeper
LoreKeeper is an application designed to help writers and storytellers organize and manage their fictional worlds. Whether you're crafting a novel, a game, or a screenplay, LoreKeeper provides the tools you need to keep track of characters, locations, events, and more. It contains claims about the fictional world which can be retrieved by searching with LLM based RAG (Retrieval-Augmented Generation).

## Features
- **World Management**: Create and manage multiple fictional worlds.
- **Character Profiles**: Store detailed information about characters, including backstories, relationships, and traits.
- **Location Tracking**: Keep track of important locations in your world.
- **Event Logging**: Document significant events and plot points.
- **Search Functionality**: Use LLM-based RAG to search through your lore and
retrieve relevant information quickly.
- **Document Reference Management**: Link claims and lore to specific document snippets for traceability. These books are stored as metadata in the database, while the actual content is stored in a file system, such as AWS S3, in a .md format and a rendered PDF format.

## Components
- **Frontend**: A user-friendly web interface built with React for managing and viewing your lore.
- **LoreKeeper BookGen**: A service that generates well-formatted books from the stored lore and format in the .md format. So it inputs the text and outputs a rendered PDF format.
- **LoreKeeper API**: A RESTful API built with FastAPI to handle all backend operations.
- **LoreKeeper LoreGen**: A service that utilizes agentic LLM to generate new lore and create claims and documents (including books) based on existing and newly generated lore.
- **Database**: PostgreSQL database to store all lore-related data.
- **File Storage**: AWS S3 for storing document contents.

## Monorepo Development

This repository is organized as a monorepo. Development workflows and command shortcuts are documented in [DEVELOPMENT.md](DEVELOPMENT.md) and [JUSTFILE.md](JUSTFILE.md).

The shared Python virtual environment lives at `.venv/` in the repo root and is used by default when running root-level `just` commands.
