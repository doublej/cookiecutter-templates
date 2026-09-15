from flask import Flask, Response, jsonify, request

from {{ cookiecutter.project_slug.replace('-', '_') }}.i18n import BASE_LOCALE, LOCALES, t

app = Flask(__name__)


def get_locale() -> str:
    """Negotiate the response language from the Accept-Language header."""
    return request.accept_languages.best_match(LOCALES) or BASE_LOCALE


@app.after_request
def add_language_headers(response: Response) -> Response:
    response.headers["Content-Language"] = get_locale()
    response.vary.add("Accept-Language")
    return response


@app.route("/")
def root():
    name = "{{ cookiecutter.project_name }}"
    return jsonify(message=t("root.message", get_locale(), name=name))


@app.route("/health")
def health():
    return jsonify(status="ok")


if __name__ == "__main__":
    app.run()
