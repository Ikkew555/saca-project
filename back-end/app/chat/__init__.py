# back-end/app/chat/__init__.py
from .routes import chat_bp  # /api/chat
from .suggestions import suggestion_bp  # /api/suggestions

__all__ = ["chat_bp", "suggestion_bp"]
