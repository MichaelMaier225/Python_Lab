from flask import Flask, render_template_string, send_from_directory
import os

app = Flask(__name__)

@app.route('/')
def home():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(base_dir, 'Snake.html')
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return render_template_string(html_content)

# Serve the CSS file manually
@app.route('/Snake.css')
def serve_css():
    return send_from_directory(os.path.dirname(__file__), 'Snake.css')

if __name__ == '__main__':
    app.run(debug=True)
