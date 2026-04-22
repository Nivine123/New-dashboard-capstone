"""Deployment-friendly Streamlit entrypoint.

Streamlit Community Cloud looks for ``streamlit_app.py`` by default.
Importing ``app`` keeps the existing multipage app structure unchanged.
"""

from app import *  # noqa: F401,F403
