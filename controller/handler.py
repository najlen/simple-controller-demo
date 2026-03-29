import os
import datetime
import kopf
import httpx

MESSAGE_BOARD_URL = os.environ.get("MESSAGE_BOARD_URL", "http://message-board-api:8080")


def _now() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def _api_url(path: str) -> str:
    return f"{MESSAGE_BOARD_URL}{path}"


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------
@kopf.on.create("demo.example.com", "v1", "messages")
def on_create(spec, patch, logger, **kwargs):
    board = spec.get("board", "general")
    payload = {
        "author": spec["author"],
        "title": spec["title"],
        "body": spec["body"],
    }
    logger.info(f"Creating message on board '{board}': {payload['title']!r}")
    try:
        resp = httpx.post(_api_url(f"/boards/{board}/messages"), json=payload, timeout=10)
        resp.raise_for_status()
    except httpx.RequestError as exc:
        logger.warning(f"Network error: {exc}")
        patch.status["phase"] = "Error"
        patch.status["error"] = str(exc)
        patch.status["lastSyncTime"] = _now()
        raise kopf.TemporaryError(str(exc), delay=15)

    data = resp.json()
    patch.status["phase"] = "Posted"
    patch.status["messageId"] = data["message_id"]
    patch.status["boardUrl"] = data["board_url"]
    patch.status["lastSyncTime"] = _now()
    patch.status["error"] = ""
    logger.info(f"Posted — messageId={data['message_id']}")


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------
@kopf.on.update("demo.example.com", "v1", "messages")
def on_update(spec, status, patch, logger, **kwargs):
    board = spec.get("board", "general")
    message_id = status.get("messageId")
    if not message_id:
        logger.warning("No messageId in status; skipping update")
        return

    payload = {
        "author": spec["author"],
        "title": spec["title"],
        "body": spec["body"],
    }
    logger.info(f"Updating message {message_id} on board '{board}'")
    try:
        resp = httpx.put(
            _api_url(f"/boards/{board}/messages/{message_id}"),
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
    except httpx.RequestError as exc:
        logger.warning(f"Network error: {exc}")
        patch.status["phase"] = "Error"
        patch.status["error"] = str(exc)
        patch.status["lastSyncTime"] = _now()
        raise kopf.TemporaryError(str(exc), delay=15)

    patch.status["phase"] = "Updated"
    patch.status["lastSyncTime"] = _now()
    patch.status["error"] = ""
    logger.info(f"Updated — messageId={message_id}")


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------
@kopf.on.delete("demo.example.com", "v1", "messages")
def on_delete(spec, status, patch, logger, **kwargs):
    board = spec.get("board", "general")
    message_id = status.get("messageId")
    if not message_id:
        logger.info("No messageId in status; nothing to delete from external API")
        return

    logger.info(f"Deleting message {message_id} from board '{board}'")
    try:
        resp = httpx.delete(
            _api_url(f"/boards/{board}/messages/{message_id}"),
            timeout=10,
        )
        if resp.status_code == 404:
            logger.info("Message already absent from external API — safe to ignore")
        else:
            resp.raise_for_status()
    except httpx.RequestError as exc:
        logger.warning(f"Network error during delete: {exc}")
        raise kopf.TemporaryError(str(exc), delay=15)

    logger.info(f"Deleted from external API — messageId={message_id}")
