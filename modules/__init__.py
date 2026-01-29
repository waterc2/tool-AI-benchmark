# Pages package - UI components for the LLM Benchmarker app
"""
This package contains the UI pages for the application.
Each page is in its own module for better maintainability.
"""

import json
import time
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# Common database imports
from database import (
    get_stats,
    get_all_test_cases,
    delete_test_case,
    save_test_case,
    clear_cache,
    get_all_models,
    get_eval_history,
    delete_eval_record,
    get_model_summary_stats,
    get_model_detail_stats,
    get_case_summary_stats,
    get_case_model_ranking,
    get_model_speed_ranking
)
