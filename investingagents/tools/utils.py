import base64



def bytes2image(raw: bytes) -> list:
    """Convert PNG bytes to an OpenAI-compatible image_url content block list."""
    if not isinstance(raw, (bytes, bytearray)):
        return [str(raw)]
    b64 = base64.b64encode(raw).decode("utf-8")
    return [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}]