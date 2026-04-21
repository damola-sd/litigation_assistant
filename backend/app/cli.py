import uvicorn


def dev() -> None:
    uvicorn.run("app.main:app", reload=True, host="127.0.0.1", port=8000)
