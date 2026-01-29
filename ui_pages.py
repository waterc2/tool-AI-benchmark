"""
UI Pages module - Re-export layer for backward compatibility.

This module re-exports all page rendering functions from the pages package,
allowing existing code (like app.py) to continue importing from ui_pages.py
without any changes.

The actual implementations have been refactored into separate modules:
- pages/sidebar.py       - render_sidebar
- pages/case_manager.py  - render_case_manager  
- pages/test_runner.py   - render_test_runner
- pages/history.py       - render_history
- pages/stats.py         - render_stats
"""

from modules.sidebar import render_sidebar
from modules.case_manager import render_case_manager
from modules.test_runner import render_test_runner
from modules.history import render_history
from modules.stats import render_stats

__all__ = [
    'render_sidebar',
    'render_case_manager',
    'render_test_runner',
    'render_history',
    'render_stats'
]