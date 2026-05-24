from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from scalar_fastapi import Layout, Theme, get_scalar_api_reference

app = FastAPI(
    title="{{ cookiecutter.project_name }}",
    description="{{ cookiecutter.description }}",
    version="0.1.0",
    docs_url=None,
)


@app.get("/")
def root():
    return {"message": "Hello from {{ cookiecutter.project_name }}"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/docs", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title,
        theme=Theme.PURPLE,
        layout=Layout.MODERN,
        dark_mode=True,
    )


@app.get("/swagger", include_in_schema=False)
async def swagger_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} — Swagger UI",
        swagger_ui_parameters={
            "docExpansion": "none",
            "displayRequestDuration": True,
            "filter": True,
            "persistAuthorization": True,
        },
    )
