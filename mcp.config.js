// mcp.config.js
module.exports = {
    tools: [
      {
        name: "start-server",
        command: "uvicorn src.main:app --reload",
        description: "Run FastAPI dev server"
      },
      {
        name: "run-tests",
        command: "pytest",
        description: "Run tests"
      },
      {
        name: "migrate",
        command: "alembic upgrade head",
        description: "Run DB migrations"
      }
    ]
  }