from pydantic import BaseModel


class WatchedFileRead(BaseModel):
    filename: str
    status: str
    detail: str | None = None


class WatchedFolderRead(BaseModel):
    folder_path: str
    files: list[WatchedFileRead]
