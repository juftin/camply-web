# Implementation plan

Add Granian with reload support to the server extra and retain Uvicorn. Exec
Granian in ASGI mode for the distributed API and route the development task
through that launcher. Wrap the Granian target with trusted proxy handling.
Use native Granian settings in Compose and Helm and document their equivalents
for existing deployments.

Verify optional dependency boundaries, CLI argument forwarding, development
reload, and startup and shutdown of both installed serving modes.
