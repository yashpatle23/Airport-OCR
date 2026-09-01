"""Application exceptions translated to stable API problem details."""

from __future__ import annotations

from typing import Any, Dict, Optional


class ApplicationError(Exception):
    """Expected request/application error with an HTTP-safe public message."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        title: str,
        detail: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.title = title
        self.detail = detail
        self.context = context or {}
