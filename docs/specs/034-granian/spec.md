# Granian distributed HTTP server

Replace Gunicorn with Granian for distributed API serving and the development
task. Standalone continues to use Uvicorn with one process for the API, bundled
frontend, and local scheduler.

The distributed launcher migrates before serving unless explicitly skipped.
It supports configurable worker counts, bind settings, access logging,
trusted proxy headers, and native CLI arguments. Base and worker-only installs
remain independent of both HTTP servers.
