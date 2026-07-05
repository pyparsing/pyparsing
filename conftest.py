import sys


def pytest_report_header(config, start_path):
    # 1. Fetch the JIT state safely (using .is_enabled() for global status)
    jit_supported = getattr(sys, "_jit", None) is not None
    jit_status = "Enabled" if (jit_supported and sys._jit.is_enabled()) else "Disabled"
    if not jit_supported:
        jit_status = "Not Supported by Python Binary"

    # 2. Fetch the GIL status (Free-threaded Python 3.13+)
    gil_supported = hasattr(sys, "_get_gil_config")
    if gil_supported:
        # sys._get_gil_config() returns a dict, e.g., {'enabled': True}
        gil_active = sys._get_gil_config().get("enabled", True)
        gil_status = "Active (Standard)" if gil_active else "Disabled (Free-Threaded)"
    else:
        gil_status = "Active (Standard CPython)"

    # Return lines to inject directly beneath rootdir/cachedir
    return [f"JIT compiler: {jit_status}", f"GIL status:   {gil_status}"]
