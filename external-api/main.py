import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Message Board API")

# In-memory store: { board_name: { message_id: {...} } }
boards: dict[str, dict[str, dict]] = {}


class MessageCreate(BaseModel):
    author: str
    title: str
    body: str


class MessageUpdate(BaseModel):
    author: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None


@app.get("/")
def health():
    return {"status": "ok"}


@app.get("/boards")
def list_boards():
    return {"boards": list(boards.keys())}


@app.get("/boards/{board}")
def list_messages(board: str):
    return {"board": board, "messages": list(boards.get(board, {}).values())}


@app.post("/boards/{board}/messages", status_code=201)
def create_message(board: str, msg: MessageCreate):
    if board not in boards:
        boards[board] = {}
    message_id = str(uuid.uuid4())
    boards[board][message_id] = {
        "id": message_id,
        "board": board,
        "author": msg.author,
        "title": msg.title,
        "body": msg.body,
    }
    board_url = f"/boards/{board}/messages/{message_id}"
    return {"message_id": message_id, "board_url": board_url}


@app.put("/boards/{board}/messages/{message_id}")
def update_message(board: str, message_id: str, msg: MessageUpdate):
    if board not in boards or message_id not in boards[board]:
        raise HTTPException(status_code=404, detail="Message not found")
    stored = boards[board][message_id]
    if msg.author is not None:
        stored["author"] = msg.author
    if msg.title is not None:
        stored["title"] = msg.title
    if msg.body is not None:
        stored["body"] = msg.body
    return {"message_id": message_id, "board_url": f"/boards/{board}/messages/{message_id}"}


@app.delete("/boards/{board}/messages/{message_id}", status_code=204)
def delete_message(board: str, message_id: str):
    if board not in boards or message_id not in boards[board]:
        raise HTTPException(status_code=404, detail="Message not found")
    del boards[board][message_id]
