# backend/app.py
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import os
import openai
import json
import tempfile
import zipfile
from datetime import datetime

app = Flask(__name__)
CORS(app)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise RuntimeError('Set OPENAI_API_KEY environment variable')
openai.api_key = OPENAI_API_KEY

MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
MAX_TOKENS = int(os.getenv('MAX_GENERATION_TOKENS', '2400'))

SYSTEM_PROMPT = (
    "You are an expert software engineer and project generator.\n"
    "When given a user's request, produce a JSON object mapping file paths to file contents.\n"
    "The JSON must be a single top-level object where keys are relative file paths (e.g., 'src/App.js') and values are raw file contents as strings.\n"
    "Do NOT include any additional commentary, only return valid JSON.\n"
    "If a large project is requested, produce a complete runnable scaffold (package.json, README, etc.).\n"
)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json or {}
    prompt = data.get('prompt', '').strip()
    project_name = data.get('project_name', 'generated_project').strip()
    if not prompt:
        return jsonify({'error': 'prompt is required'}), 400

    user_prompt = (
        f"User request: {prompt}\n\n"
        f"Respond with a JSON object mapping filenames to file content strings. "
        f"The root folder should be named `{project_name}`. Include README.md and a run/deploy instruction file if relevant."
    )

    # Call OpenAI
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        resp = openai.ChatCompletion.create(
            model=MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=0.2,
        )
    except Exception as e:
        return jsonify({'error': 'OpenAI API failed', 'detail': str(e)}), 500

    text = resp['choices'][0]['message']['content']

    # Attempt to parse JSON from the model output
    try:
        # In case model wraps JSON in code fences, strip them
        if text.strip().startswith('```'):
            # remove triple backticks and optional json
            parts = text.split('```')
            # choose the longest chunk assuming it's JSON
            candidate = max(parts, key=len)
        else:
            candidate = text
        files = json.loads(candidate)
    except Exception as e:
        # Return model output for debugging in case of parse failure
        return jsonify({'error': 'failed to parse JSON from model', 'model_output': text, 'detail': str(e)}), 500

    # Create temp directory and write files
    tmpdir = tempfile.mkdtemp(prefix='ai_gen_')
    project_root = os.path.join(tmpdir, project_name)
    os.makedirs(project_root, exist_ok=True)

    for path, content in files.items():
        # sanitize path
        safe_path = os.path.normpath(os.path.join(project_root, path))
        if not safe_path.startswith(project_root):
            continue
        dirpath = os.path.dirname(safe_path)
        if dirpath and not os.path.exists(dirpath):
            os.makedirs(dirpath, exist_ok=True)
        # Write bytes for binary-like files if the model encodes them (rare)
        with open(safe_path, 'w', encoding='utf-8') as f:
            f.write(content)

    # Zip the folder
    zip_path = os.path.join(tmpdir, f"{project_name}.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, filenames in os.walk(project_root):
            for fname in filenames:
                full = os.path.join(root, fname)
                arcname = os.path.relpath(full, project_root)
                zf.write(full, arcname)

    return send_file(zip_path, as_attachment=True, download_name=f"{project_name}.zip")
@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'time': datetime.utcnow().isoformat()})

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Project Generator</title>
        <style>
            body { font-family: Arial, sans-serif; background: #f9fafc; text-align: center; padding: 50px; }
            h1 { color: #333; }
            p { color: #555; }
            input, textarea, button { padding: 10px; margin: 10px; width: 80%; max-width: 500px; }
            button { background: #4CAF50; color: white; border: none; cursor: pointer; }
            button:hover { background: #45a049; }
            .container { max-width: 600px; margin: auto; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 AI Project Generator</h1>
            <p>Enter your project idea below, and we'll create a downloadable zip for you.</p>
            <textarea id="prompt" rows="4" placeholder="Describe your project..."></textarea><br>
            <input id="name" type="text" placeholder="Project name (optional)" /><br>
            <button onclick="generateProject()">Generate Project</button>
            <p id="status"></p>
        </div>

        <script>
            async function generateProject() {
                const prompt = document.getElementById('prompt').value;
                const projectName = document.getElementById('name').value || "generated_project";
                document.getElementById('status').innerText = "Generating...";
                
                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: prompt, project_name: projectName })
                });

                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = projectName + '.zip';
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    document.getElementById('status').innerText = "✅ Done! Your download should start.";
                } else {
                    const err = await response.json();
                    document.getElementById('status').innerText = "❌ Error: " + err.error;
                }
            }
        </script>
    </body>
    </html>
    """
@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'time': datetime.utcnow().isoformat()})
@app.route('/')
def home():
    return """
    <h1>🚀 AI Project Generator</h1>
    <p>Use the <code>/generate</code> endpoint to create your project.</p>
    <p>Health check: <a href='/health'>/health</a></p>
    """
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
