import os
import warnings

__version__ = "0.8.2"

# Filter internal third-party library warnings unless running with ACE_DEBUG=1
if not os.getenv("ACE_DEBUG"):
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
