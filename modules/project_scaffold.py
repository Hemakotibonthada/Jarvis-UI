"""
Project Scaffolder — Generate project boilerplate for various frameworks.
"""

import os
from pathlib import Path
from core.logger import get_logger

log = get_logger("scaffolder")


class ProjectScaffolder:
    """Generate project scaffolding for various tech stacks."""

    def scaffold_project(self, project_type: str, project_name: str,
                         output_dir: str = "", **kwargs) -> str:
        """Create a new project with boilerplate."""
        if not output_dir:
            output_dir = str(Path.home() / "Projects")

        root = Path(output_dir) / project_name
        if root.exists():
            return f"Directory already exists: {root}"

        scaffolders = {
            "python": self._scaffold_python,
            "python_api": self._scaffold_python_api,
            "react": self._scaffold_react,
            "node": self._scaffold_node,
            "node_api": self._scaffold_node_api,
            "html": self._scaffold_html,
            "flask": self._scaffold_flask,
            "django": self._scaffold_django_basic,
            "cli": self._scaffold_cli,
            "chrome_extension": self._scaffold_chrome_ext,
            "electron": self._scaffold_electron,
            "arduino": self._scaffold_arduino,
        }

        handler = scaffolders.get(project_type)
        if not handler:
            return f"Unknown project type: {project_type}. Available: {', '.join(scaffolders.keys())}"

        try:
            handler(root, project_name, **kwargs)
            file_count = sum(1 for _ in root.rglob("*") if _.is_file())
            return f"Project '{project_name}' created at {root}\n  Type: {project_type}\n  Files: {file_count}"
        except Exception as e:
            return f"Scaffolding error: {e}"

    def _write(self, path: Path, content: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _scaffold_python(self, root: Path, name: str, **kw):
        self._write(root / "main.py", f'"""\n{name} — Main entry point.\n"""\n\n\ndef main():\n    print("Hello from {name}!")\n\n\nif __name__ == "__main__":\n    main()\n')
        self._write(root / f"{name.lower().replace(' ', '_')}/__init__.py", f'"""{name} package."""\n\n__version__ = "0.1.0"\n')
        self._write(root / "tests/__init__.py", "")
        self._write(root / "tests/test_main.py", f'"""Tests for {name}."""\n\n\ndef test_placeholder():\n    assert True\n')
        self._write(root / "requirements.txt", "# Project dependencies\n")
        self._write(root / ".gitignore", "__pycache__/\n*.pyc\n.env\nvenv/\ndist/\n*.egg-info/\n.pytest_cache/\n")
        self._write(root / "README.md", f"# {name}\n\n## Setup\n```bash\npip install -r requirements.txt\npython main.py\n```\n")
        self._write(root / "setup.py", f'from setuptools import setup, find_packages\n\nsetup(\n    name="{name}",\n    version="0.1.0",\n    packages=find_packages(),\n    python_requires=">=3.9",\n)\n')
        self._write(root / ".env.example", "# Environment variables\n")
        self._write(root / "pyproject.toml", f'[tool.pytest.ini_options]\ntestpaths = ["tests"]\n\n[project]\nname = "{name}"\nversion = "0.1.0"\n')

    def _scaffold_python_api(self, root: Path, name: str, **kw):
        self._scaffold_python(root, name)
        self._write(root / "app/__init__.py", "")
        self._write(root / "app/main.py", f'"""\n{name} API Server\n"""\n\nfrom fastapi import FastAPI\n\napp = FastAPI(title="{name}", version="0.1.0")\n\n\n@app.get("/")\nasync def root():\n    return {{"message": "Welcome to {name}"}}\n\n\n@app.get("/health")\nasync def health():\n    return {{"status": "ok"}}\n')
        self._write(root / "app/models.py", '"""Data models."""\n\nfrom pydantic import BaseModel\n\n\nclass Item(BaseModel):\n    name: str\n    description: str = ""\n    price: float\n    in_stock: bool = True\n')
        self._write(root / "app/routes/__init__.py", "")
        self._write(root / "app/routes/items.py", '"""Item routes."""\n\nfrom fastapi import APIRouter\n\nrouter = APIRouter(prefix="/items", tags=["items"])\n\n\n@router.get("/")\nasync def list_items():\n    return []\n')
        self._write(root / "requirements.txt", "fastapi>=0.100.0\nuvicorn[standard]>=0.23.0\npydantic>=2.0.0\n")
        self._write(root / "Dockerfile", f'FROM python:3.11-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\nCMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]\n')

    def _scaffold_flask(self, root: Path, name: str, **kw):
        self._write(root / "app/__init__.py", f'from flask import Flask\n\ndef create_app():\n    app = Flask(__name__)\n    app.config["SECRET_KEY"] = "change-me"\n\n    from .routes import main_bp\n    app.register_blueprint(main_bp)\n\n    return app\n')
        self._write(root / "app/routes.py", 'from flask import Blueprint, render_template, jsonify\n\nmain_bp = Blueprint("main", __name__)\n\n\n@main_bp.route("/")\ndef index():\n    return render_template("index.html")\n\n\n@main_bp.route("/api/health")\ndef health():\n    return jsonify({"status": "ok"})\n')
        self._write(root / "app/templates/index.html", f'<!DOCTYPE html>\n<html>\n<head><title>{name}</title></head>\n<body><h1>{name}</h1></body>\n</html>\n')
        self._write(root / "app/static/.gitkeep", "")
        self._write(root / "run.py", 'from app import create_app\n\napp = create_app()\n\nif __name__ == "__main__":\n    app.run(debug=True)\n')
        self._write(root / "requirements.txt", "flask>=3.0.0\n")
        self._write(root / ".gitignore", "__pycache__/\n*.pyc\n.env\nvenv/\ninstance/\n")
        self._write(root / "README.md", f"# {name}\n\nFlask application.\n\n```bash\npip install -r requirements.txt\npython run.py\n```\n")

    def _scaffold_django_basic(self, root: Path, name: str, **kw):
        safe = name.lower().replace(" ", "_").replace("-", "_")
        self._write(root / "manage.py", f'#!/usr/bin/env python\nimport os\nimport sys\n\ndef main():\n    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "{safe}.settings")\n    from django.core.management import execute_from_command_line\n    execute_from_command_line(sys.argv)\n\nif __name__ == "__main__":\n    main()\n')
        self._write(root / f"{safe}/__init__.py", "")
        self._write(root / f"{safe}/settings.py", f'"""\n{name} Django settings.\n"""\n\nfrom pathlib import Path\n\nBASE_DIR = Path(__file__).resolve().parent.parent\nSECRET_KEY = "change-me-in-production"\nDEBUG = True\nALLOWED_HOSTS = ["*"]\nINSTALLED_APPS = [\n    "django.contrib.admin",\n    "django.contrib.auth",\n    "django.contrib.contenttypes",\n    "django.contrib.sessions",\n    "django.contrib.messages",\n    "django.contrib.staticfiles",\n]\nMIDDLEWARE = [\n    "django.middleware.security.SecurityMiddleware",\n    "django.contrib.sessions.middleware.SessionMiddleware",\n    "django.middleware.common.CommonMiddleware",\n    "django.middleware.csrf.CsrfViewMiddleware",\n    "django.contrib.auth.middleware.AuthenticationMiddleware",\n    "django.contrib.messages.middleware.MessageMiddleware",\n]\nROOT_URLCONF = "{safe}.urls"\nDATABASES = {{\n    "default": {{\n        "ENGINE": "django.db.backends.sqlite3",\n        "NAME": BASE_DIR / "db.sqlite3",\n    }}\n}}\nSTATIC_URL = "static/"\n')
        self._write(root / f"{safe}/urls.py", f'from django.contrib import admin\nfrom django.urls import path\n\nurlpatterns = [\n    path("admin/", admin.site.urls),\n]\n')
        self._write(root / f"{safe}/wsgi.py", f'import os\nfrom django.core.wsgi import get_wsgi_application\nos.environ.setdefault("DJANGO_SETTINGS_MODULE", "{safe}.settings")\napplication = get_wsgi_application()\n')
        self._write(root / "requirements.txt", "django>=5.0\n")
        self._write(root / ".gitignore", "__pycache__/\ndb.sqlite3\n.env\n*.pyc\nmedia/\nstaticfiles/\n")

    def _scaffold_node(self, root: Path, name: str, **kw):
        self._write(root / "package.json", f'{{\n  "name": "{name.lower()}",\n  "version": "1.0.0",\n  "description": "{name}",\n  "main": "index.js",\n  "scripts": {{\n    "start": "node index.js",\n    "dev": "nodemon index.js",\n    "test": "jest"\n  }},\n  "keywords": [],\n  "license": "MIT"\n}}\n')
        self._write(root / "index.js", f'/**\n * {name}\n */\n\nconsole.log("Hello from {name}!");\n')
        self._write(root / ".gitignore", "node_modules/\n.env\ndist/\ncoverage/\n")
        self._write(root / "README.md", f"# {name}\n\n```bash\nnpm install\nnpm start\n```\n")
        self._write(root / ".env.example", "NODE_ENV=development\nPORT=3000\n")

    def _scaffold_node_api(self, root: Path, name: str, **kw):
        self._scaffold_node(root, name)
        self._write(root / "package.json", f'{{\n  "name": "{name.lower()}",\n  "version": "1.0.0",\n  "main": "src/server.js",\n  "scripts": {{\n    "start": "node src/server.js",\n    "dev": "nodemon src/server.js",\n    "test": "jest"\n  }}\n}}\n')
        self._write(root / "src/server.js", f'const express = require("express");\nconst cors = require("cors");\n\nconst app = express();\nconst PORT = process.env.PORT || 3000;\n\napp.use(cors());\napp.use(express.json());\n\napp.get("/", (req, res) => {{\n  res.json({{ message: "Welcome to {name}" }});\n}});\n\napp.get("/api/health", (req, res) => {{\n  res.json({{ status: "ok" }});\n}});\n\napp.listen(PORT, () => {{\n  console.log(`Server running on port ${{PORT}}`);\n}});\n')
        self._write(root / "src/routes/index.js", 'const express = require("express");\nconst router = express.Router();\n\nmodule.exports = router;\n')
        self._write(root / "src/middleware/auth.js", '// Authentication middleware\nmodule.exports = (req, res, next) => {\n  // TODO: Implement auth\n  next();\n};\n')

    def _scaffold_react(self, root: Path, name: str, **kw):
        self._write(root / "package.json", f'{{\n  "name": "{name.lower()}",\n  "version": "0.1.0",\n  "private": true,\n  "scripts": {{\n    "start": "react-scripts start",\n    "build": "react-scripts build",\n    "test": "react-scripts test"\n  }},\n  "dependencies": {{\n    "react": "^18.0.0",\n    "react-dom": "^18.0.0",\n    "react-scripts": "5.0.0"\n  }}\n}}\n')
        self._write(root / "public/index.html", f'<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="utf-8" />\n  <meta name="viewport" content="width=device-width, initial-scale=1" />\n  <title>{name}</title>\n</head>\n<body>\n  <div id="root"></div>\n</body>\n</html>\n')
        self._write(root / "src/index.js", 'import React from "react";\nimport ReactDOM from "react-dom/client";\nimport App from "./App";\nimport "./index.css";\n\nconst root = ReactDOM.createRoot(document.getElementById("root"));\nroot.render(<App />);\n')
        self._write(root / "src/App.js", f'import React from "react";\n\nfunction App() {{\n  return (\n    <div className="App">\n      <h1>{name}</h1>\n      <p>Edit src/App.js and save to reload.</p>\n    </div>\n  );\n}}\n\nexport default App;\n')
        self._write(root / "src/index.css", 'body {\n  margin: 0;\n  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", sans-serif;\n}\n')
        self._write(root / "src/components/.gitkeep", "")
        self._write(root / ".gitignore", "node_modules/\nbuild/\n.env\n")

    def _scaffold_html(self, root: Path, name: str, **kw):
        self._write(root / "index.html", f'<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n  <title>{name}</title>\n  <link rel="stylesheet" href="css/style.css">\n</head>\n<body>\n  <header>\n    <h1>{name}</h1>\n  </header>\n  <main>\n    <p>Welcome to {name}!</p>\n  </main>\n  <footer>\n    <p>&copy; {name} 2025</p>\n  </footer>\n  <script src="js/main.js"></script>\n</body>\n</html>\n')
        self._write(root / "css/style.css", '* { margin: 0; padding: 0; box-sizing: border-box; }\n\nbody {\n  font-family: system-ui, sans-serif;\n  line-height: 1.6;\n  color: #333;\n}\n\nheader { background: #333; color: white; padding: 1rem; text-align: center; }\nmain { max-width: 800px; margin: 2rem auto; padding: 0 1rem; }\nfooter { text-align: center; padding: 1rem; color: #666; }\n')
        self._write(root / "js/main.js", f'// {name} JavaScript\nconsole.log("{name} loaded!");\n')
        self._write(root / "images/.gitkeep", "")

    def _scaffold_cli(self, root: Path, name: str, **kw):
        safe = name.lower().replace(" ", "_").replace("-", "_")
        self._write(root / f"{safe}.py", f'"""\n{name} — CLI Application\n"""\n\nimport argparse\nimport sys\n\n\ndef main():\n    parser = argparse.ArgumentParser(description="{name}")\n    parser.add_argument("command", help="Command to run")\n    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")\n    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")\n\n    args = parser.parse_args()\n\n    if args.verbose:\n        print(f"Running command: {{args.command}}")\n\n    print(f"Hello from {name}!")\n\n\nif __name__ == "__main__":\n    main()\n')
        self._write(root / "requirements.txt", "# CLI dependencies\n")
        self._write(root / ".gitignore", "__pycache__/\n*.pyc\n.env\nvenv/\n")
        self._write(root / "README.md", f"# {name}\n\nCLI tool.\n\n```bash\npython {safe}.py --help\n```\n")

    def _scaffold_chrome_ext(self, root: Path, name: str, **kw):
        self._write(root / "manifest.json", f'{{\n  "manifest_version": 3,\n  "name": "{name}",\n  "version": "1.0.0",\n  "description": "{name} Chrome Extension",\n  "permissions": ["activeTab", "storage"],\n  "action": {{\n    "default_popup": "popup.html",\n    "default_icon": "icon.png"\n  }},\n  "background": {{\n    "service_worker": "background.js"\n  }}\n}}\n')
        self._write(root / "popup.html", f'<!DOCTYPE html>\n<html>\n<head><style>body {{ width: 300px; padding: 10px; font-family: sans-serif; }}</style></head>\n<body>\n  <h2>{name}</h2>\n  <p>Extension popup</p>\n  <button id="action">Click me</button>\n  <script src="popup.js"></script>\n</body>\n</html>\n')
        self._write(root / "popup.js", 'document.getElementById("action").addEventListener("click", () => {\n  chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {\n    console.log("Active tab:", tabs[0].url);\n  });\n});\n')
        self._write(root / "background.js", f'// {name} background service worker\nconsole.log("{name} extension loaded");\n')
        self._write(root / "content.js", '// Content script\nconsole.log("Content script loaded");\n')

    def _scaffold_electron(self, root: Path, name: str, **kw):
        self._write(root / "package.json", f'{{\n  "name": "{name.lower()}",\n  "version": "1.0.0",\n  "main": "main.js",\n  "scripts": {{\n    "start": "electron ."\n  }},\n  "devDependencies": {{\n    "electron": "^28.0.0"\n  }}\n}}\n')
        self._write(root / "main.js", f'const {{ app, BrowserWindow }} = require("electron");\n\nfunction createWindow() {{\n  const win = new BrowserWindow({{\n    width: 1200,\n    height: 800,\n    webPreferences: {{ nodeIntegration: true, contextIsolation: false }},\n  }});\n  win.loadFile("index.html");\n}}\n\napp.whenReady().then(createWindow);\napp.on("window-all-closed", () => {{ if (process.platform !== "darwin") app.quit(); }});\n')
        self._write(root / "index.html", f'<!DOCTYPE html>\n<html>\n<head><title>{name}</title>\n<style>body {{ font-family: system-ui; padding: 20px; background: #1a1a2e; color: #eee; }}</style></head>\n<body>\n  <h1>{name}</h1>\n  <p>Electron Desktop App</p>\n</body>\n</html>\n')

    def _scaffold_arduino(self, root: Path, name: str, **kw):
        safe = name.replace(" ", "_")
        self._write(root / f"{safe}/{safe}.ino", f'/*\n * {name}\n * Arduino Project\n */\n\nvoid setup() {{\n  Serial.begin(115200);\n  Serial.println("{name} starting...");\n  pinMode(LED_BUILTIN, OUTPUT);\n}}\n\nvoid loop() {{\n  digitalWrite(LED_BUILTIN, HIGH);\n  delay(500);\n  digitalWrite(LED_BUILTIN, LOW);\n  delay(500);\n}}\n')
        self._write(root / "README.md", f"# {name}\n\nArduino project.\n")

    def list_templates(self) -> str:
        """List available project templates."""
        templates = {
            "python": "Basic Python project with tests, setup.py, and gitignore",
            "python_api": "FastAPI REST API project with Docker",
            "flask": "Flask web application with templates",
            "django": "Django web framework project",
            "node": "Node.js project with npm",
            "node_api": "Express.js REST API",
            "react": "React frontend application",
            "html": "Static HTML/CSS/JS website",
            "cli": "Python CLI tool with argparse",
            "chrome_extension": "Chrome extension (Manifest V3)",
            "electron": "Electron desktop application",
            "arduino": "Arduino/ESP32 project",
        }
        lines = [f"  {k:<20} — {v}" for k, v in templates.items()]
        return "Available project templates:\n" + "\n".join(lines)


# ─── Singleton ────────────────────────────────────────────────
scaffolder = ProjectScaffolder()
