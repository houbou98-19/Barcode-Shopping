import json
import queue

_subscribers = set()

# How often to send a keepalive comment on idle connections, so
# intermediary proxies (e.g. Nginx Proxy Manager) don't time out and
# silently drop a connection that's just waiting for the next event.
KEEPALIVE_SECONDS = 15


def subscribe():
    """Registers a new listener queue and yields SSE-formatted messages from
    it until the client disconnects (the generator is abandoned by Flask)."""
    q = queue.Queue()
    _subscribers.add(q)
    try:
        while True:
            try:
                message = q.get(timeout=KEEPALIVE_SECONDS)
                yield f"data: {json.dumps(message)}\n\n"
            except queue.Empty:
                yield ": keepalive\n\n"
    finally:
        _subscribers.discard(q)


def broadcast(event_type):
    """Notifies every connected client that something changed. Payload is
    just a type, not the data itself - clients already know how to refetch
    the list, so there's nothing to gain from duplicating it here."""
    for q in _subscribers:
        q.put({"type": event_type})
