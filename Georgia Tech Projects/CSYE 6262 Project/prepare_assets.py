"""Prepare assets and the isolated RF runtime using the existing Render build command."""

from scripts.prepare_assets import main
from scripts.setup_rf_runtime import main as setup_rf_runtime


if __name__ == "__main__":
    main()
    setup_rf_runtime()
