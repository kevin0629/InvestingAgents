import os

    
def get_backend_base_url() -> str:
    """Get the backend base URL from environment or default."""
    return os.getenv("BACKEND_API_URL", "http://localhost:8000")
