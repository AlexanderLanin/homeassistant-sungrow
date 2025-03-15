# poetry, pip, uv, ...

*2025-03-15*

For some reason, I don't remember why, poetry was used in this project.
However using venv inside devcontainers was always a pain. Maybe it was done incorrectly, or it's just not meant to be used that way.

Either way, I'm going to switch back to using `pip` and `requirements.txt` files. This is a more standard way of doing things and will be easier to maintain. Potentially simply due to more familiarity.

However...

As this is a learning project...

Let's use uv!


### Comparison by ChatGPT

*ChatGPT can make mistakes. Verify important information.*

| Feature                   | pip (+ pip-tools)          | uv (pip mode)              | uv (poetry mode)           | Poetry                     |
|---------------------------|----------------------------|----------------------------|----------------------------|----------------------------|
| **Package Management**    | ✅ Installs from PyPI      | ✅ Installs from PyPI      | ✅ Installs from PyPI      | ✅ Installs from PyPI      |
| **Dependency Resolution** | ✅ With `pip-compile` (PEP 508) | ✅ Full solver (PEP 508)  | ✅ Full solver (PEP 508)  | ✅ Full solver (PEP 508)  |
| **Lockfile Support**      | ✅ `requirements.txt` + `requirements.lock` (via `pip-compile`) | ✅ `requirements.lock`     | ✅ `requirements.lock`     | ✅ `poetry.lock`          |
| **Virtual Environment Mgmt** | ❌ Requires external tool | ❌ No built-in support | ✅ Manages venv (`uv venv`) | ✅ Manages venv automatically |
| **Project Metadata (`pyproject.toml`)** | ❌ No native support  | ✅ Reads `pyproject.toml` | ✅ Reads `pyproject.toml` | ✅ Full support           |
| **Editable Installs (`pip install -e .`)** | ✅ Supported | ✅ Supported | ✅ Supported | ✅ Supported |
| **Dev Dependencies**      | ✅ Uses separate `requirements-dev.txt` (via `pip-tools`) | ✅ Uses `pyproject.toml` | ✅ Uses `pyproject.toml` | ✅ Uses `pyproject.toml` |
| **Publish to PyPI**       | ❌ Requires `twine`        | ❌ No built-in support    | ❌ No built-in support    | ✅ Built-in (`poetry publish`) |
| **Dependency Grouping**   | ❌ No built-in support (workarounds with multiple `requirements-*.txt` files) | ✅ Supports groups        | ✅ Supports groups        | ✅ Supports groups        |
| **Binary Package Support** | ✅ Can install wheels     | ✅ Can install wheels     | ✅ Can install wheels     | ✅ Can install wheels     |
| **Mono Repo Support**     | ✅ Works with constraints | ✅ Works with constraints | ✅ Works with constraints | ❌ Less flexible |
| **Python Version Mgmt**   | ❌ No built-in support     | ✅ Reads `pyproject.toml` | ✅ Reads `pyproject.toml` | ✅ Reads `pyproject.toml` |
| **Ease of Use**           | ❌ Requires multiple tools (`pip`, `pip-compile`, `pip-sync`) | ✅ Simple CLI (like pip)  | ✅ Simple CLI (like Poetry) | ❌ More complex CLI       |
| **Ecosystem Integration** | ✅ Standard tool          | ✅ Growing support       | ✅ Growing support       | ✅ Well-integrated        |
