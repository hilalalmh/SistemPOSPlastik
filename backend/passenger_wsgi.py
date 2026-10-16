"""WSGI entry point for cPanel/Passenger (Jagoan Cloud Hosting MixMatch).

Passenger speaks WSGI while FastAPI is ASGI. We wrap the ASGI app with
``a2wsgi`` so it can be served from cPanel's "Setup Python App" without a
separate uvicorn process.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from a2wsgi import ASGIMiddleware  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402

application = ASGIMiddleware(fastapi_app)
