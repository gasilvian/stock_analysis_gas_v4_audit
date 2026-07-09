"""SWS Snowflake Engine v3.1 - controlled implementation of the public
GitHub Simply Wall St methodology (model pack v3.1).

Not investment advice. Not a replica of the current Simply Wall St live platform.
"""
from sws_engine.orchestration.company_run import run_company_analysis

__all__ = ["run_company_analysis"]
__version__ = "3.1.0"
