from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/")
def root():
    return jsonify(message="Hello from {{ cookiecutter.project_name }}")


@app.route("/health")
def health():
    return jsonify(status="ok")


if __name__ == "__main__":
    app.run(debug=True)
