// GREEN: scaffold проекта (pyproject.toml, ruff, mypy, pytest, mcp SDK, olefile, openpyxl, httpx)
import * as fs from 'node:fs';
import * as path from 'node:path';

export function assumption_scaffold_pyproject_toml_ruff_mypy_pytest_mcp_sdk_olef() {
  const files: Record<string, string> = {
    'pyproject.toml': `[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "onec-converter"
version = "0.1.0"
description = "MCP-сервер переноса данных между информационными базами 1С"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.2",
    "olefile>=0.47",
    "openpyxl>=3.1",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = ["pytest>=8", "pytest-asyncio>=0.23", "ruff>=0.5", "mypy>=1.10"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
python_version = "3.11"
strict = true
`,
    'pytest.ini': `[pytest]
testpaths = tests
pythonpath = src
`,
    '.gitignore': `__pycache__/
*.pyc
.venv/
venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
dist/
build/
*.egg-info/
.onec_cache/
.spike/
`,
    'src/onec_converter/__init__.py': `"""Пакет onec_converter: перенос данных между ИБ 1С."""\n`,
    'tests/__init__.py': ``,
  };
  const written: string[] = [];
  for (const [rel, content] of Object.entries(files)) {
    const p = path.resolve(process.cwd(), rel);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, content);
    written.push(rel);
  }
  return written.join(', ');
}
