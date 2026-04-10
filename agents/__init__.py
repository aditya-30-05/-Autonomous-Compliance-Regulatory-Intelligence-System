"""agents package – exposes each agent's `run()` entry-point."""
from agents import parser, diff, mapper, drafter, reporter

__all__ = ["parser", "diff", "mapper", "drafter", "reporter"]
