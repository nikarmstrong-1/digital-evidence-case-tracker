from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return """
    <h1>Digital Evidence Case Tracker</h1>
    <p>Sprint 1: basic Flask application setup.</p>
    """


if __name__ == "__main__":
    app.run(debug=True)