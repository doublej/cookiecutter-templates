from fastapi import FastAPI

app = FastAPI(title="{{ cookiecutter.project_name }}")


@app.get("/")
def root():
    return {"message": "Hello from {{ cookiecutter.project_name }}"}


@app.get("/health")
def health():
    return {"status": "ok"}
