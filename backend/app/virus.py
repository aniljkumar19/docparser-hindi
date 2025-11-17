import os, socket
CLAMAV_ENABLED = os.getenv("CLAMAV_ENABLED","false").lower() == "true"
CLAMAV_HOST = os.getenv("CLAMAV_HOST","clamd")
CLAMAV_PORT = int(os.getenv("CLAMAV_PORT","3310"))

def scan_bytes(data: bytes) -> bool:
    """Return True if clean or scanning disabled; False if infected."""
    if not CLAMAV_ENABLED:
        return True
    try:
        # Minimalistic INSTREAM to clamd
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((CLAMAV_HOST, CLAMAV_PORT))
        s.sendall(b"zINSTREAM\0")
        chunk_size = 1024
        i = 0
        while i < len(data):
            chunk = data[i:i+chunk_size]
            s.sendall(len(chunk).to_bytes(4,'big') + chunk)
            i += chunk_size
        s.sendall((0).to_bytes(4,'big'))
        resp = s.recv(4096).decode()
        s.close()
        return "OK" in resp
    except Exception:
        # If scanner not reachable, fail open (or set to False to fail close)
        return True
