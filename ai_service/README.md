# AI Query Service and Public Interface

The future FastAPI service hosts one AI agent and the public web interface.

## Planned technology

- Python;
- FastAPI;
- one AI agent;
- an MCP client using Streamable HTTP;
- HTML templates, CSS, and JavaScript served by FastAPI.

## Public endpoints

- `GET /` serves the public page;
- `POST /api/questions` processes one independent question.

The browser communicates with FastAPI through REST. No WebSocket or response streaming is planned for the MVP.

## Responsibilities

- serve the public templates and static assets;
- validate one question per request;
- call only the MCP tools needed for that question;
- answer from tool results without inventing products, branches, or quantities;
- clearly report unavailable or insufficient information;
- keep no conversation history;
- never access PostgreSQL directly.

## Public interface location

```text
ai_service/
└── app/
    ├── templates/     # Public HTML templates
    └── static/        # Public CSS and JavaScript
```

The page will contain a question field, submit button, loading indicator, response area, and clear error message. No FastAPI route, AI agent, or functional interface is implemented during Task 0.
