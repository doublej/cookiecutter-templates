from typing import Annotated

from fastapi import Depends, FastAPI, Header, Response
from fastapi.openapi.docs import get_swagger_ui_html
from scalar_fastapi import Layout, Theme, get_scalar_api_reference

from {{ cookiecutter.project_slug.replace('-', '_') }}.i18n import negotiate, t

app = FastAPI(
    title="{{ cookiecutter.project_name }}",
    description="{{ cookiecutter.description }}",
    version="0.1.0",
    docs_url=None,
)


def get_locale(
    response: Response, accept_language: Annotated[str | None, Header()] = None
) -> str:
    """Negotiate the language from Accept-Language and advertise it on the response."""
    locale = negotiate(accept_language)
    response.headers["Content-Language"] = locale
    response.headers["Vary"] = "Accept-Language"
    return locale


@app.get("/")
def root(locale: Annotated[str, Depends(get_locale)]):
    return {"message": t("root.message", locale, name=app.title)}


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
