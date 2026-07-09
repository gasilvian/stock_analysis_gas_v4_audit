"""Import Streamlit when available, otherwise provide a no-op test shim.

The production dashboard requires the optional ``dashboard`` extra. The shim
keeps import/smoke tests deterministic in environments where Streamlit is not
installed.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterable

try:  # pragma: no cover - real Streamlit path is exercised manually.
    import streamlit as st  # type: ignore
    STREAMLIT_AVAILABLE = True
except Exception:  # pragma: no cover - fallback is used in CI-like sandbox.
    STREAMLIT_AVAILABLE = False

    class _NoopColumn:
        def __enter__(self):
            return st

        def __exit__(self, exc_type, exc, tb):
            return False

    class _NoopExpander(_NoopColumn):
        pass

    class _NoopSidebar:
        def __getattr__(self, name: str):
            return getattr(st, name)

    class _NoopStreamlit:
        sidebar = _NoopSidebar()

        def __getattr__(self, name: str):
            def _method(*args: Any, **kwargs: Any):
                if name in {"columns"}:
                    spec = args[0] if args else 1
                    n = len(spec) if isinstance(spec, Iterable) and not isinstance(spec, (str, bytes)) else int(spec)
                    return [_NoopColumn() for _ in range(n)]
                if name in {"tabs"}:
                    labels = args[0] if args else []
                    return [_NoopColumn() for _ in labels]
                if name in {"expander", "container", "spinner"}:
                    return _NoopExpander()
                if name in {"selectbox"}:
                    options = list(args[1] if len(args) > 1 else kwargs.get("options", []))
                    index = kwargs.get("index", 0)
                    return options[index] if options else None
                if name in {"multiselect"}:
                    return kwargs.get("default", [])
                if name in {"text_input"}:
                    return kwargs.get("value", args[1] if len(args) > 1 else "")
                if name in {"number_input", "slider"}:
                    return kwargs.get("value", kwargs.get("min_value", 0))
                if name in {"checkbox"}:
                    return kwargs.get("value", False)
                if name in {"button"}:
                    return False
                if name in {"file_uploader"}:
                    return None
                if name in {"dataframe", "table", "plotly_chart", "json", "metric", "markdown", "caption", "warning", "error", "success", "info", "write", "title", "header", "subheader", "set_page_config", "divider"}:
                    return None
                return None
            return _method

    st = _NoopStreamlit()
