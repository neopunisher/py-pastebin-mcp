# Pastebin MCP Server

An [MCP](https://modelcontextprotocol.io/) server for the Pastebin API, built with
[FastMCP](https://gofastmcp.com/). Managed with [uv](https://docs.astral.sh/uv/) and
distributed on PyPI so it can be run directly with `uvx` — no install step, no virtualenv
to manage.

## Tools

| Tool | Description |
| --- | --- |
| `login` | Exchange username/password for a Pastebin User Key |
| `create_paste` | Create a paste (public / unlisted / private) |
| `list_user_pastes` | List your pastes (requires a User Key) |
| `delete_paste` | Delete one of your pastes |
| `get_trending_pastes` | Fetch the current trending pastes |
| `stop` | Shut the server down |

## Configuration

| Variable | Required | Description |
| --- | --- | --- |
| `PASTEBIN_DEV_KEY` | yes | Your Pastebin [developer API key](https://pastebin.com/doc_api) |
| `PASTEBIN_USER_KEY` | for private/list/delete | User Key returned by `login` |

Both can also be passed per-call as `api_dev_key` / `api_user_key` arguments.

## Run it

Once published, no installation is needed:

```bash
PASTEBIN_DEV_KEY=your_key uvx mcp-pastebin
```

Pin a version:

```bash
uvx mcp-pastebin@0.1.0
```

From a local checkout (development):

```bash
PASTEBIN_DEV_KEY=your_key uv run mcp-pastebin
```

## MCP client configuration

Add to your client's MCP config (`.mcp.json`, `claude_desktop_config.json`, etc.):

```json
{
  "mcpServers": {
    "pastebin": {
      "command": "uvx",
      "args": ["mcp-pastebin"],
      "env": {
        "PASTEBIN_DEV_KEY": "your_key"
      }
    }
  }
}
```

While developing, point `uvx` at the working tree instead:

```json
{
  "mcpServers": {
    "pastebin": {
      "command": "uvx",
      "args": ["--from", "/absolute/path/to/pastebin-mcp", "mcp-pastebin"],
      "env": { "PASTEBIN_DEV_KEY": "your_key" }
    }
  }
}
```

## Development

```bash
uv sync                 # create .venv and install deps from uv.lock
uv run mcp-pastebin     # run the server from source
uv lock --upgrade       # refresh the lockfile
uv run ruff check .     # lint
```

`uv.lock` is committed so development environments are reproducible; it does not
constrain consumers installing from PyPI.

Every push and pull request runs [`.github/workflows/ci.yml`](.github/workflows/ci.yml):
`uv sync --locked`, `ruff check .`, then `uv build` and a stdio smoke test that starts the
built wheel's console script and checks it answers an MCP `initialize` request - on Python
3.10, 3.11, 3.12 and 3.13.

## Releasing

Releases are automated: pushing a tag that starts with `v` runs
[`.github/workflows/release.yml`](.github/workflows/release.yml), which builds the sdist
and wheel with `uv build`, smoke-tests the built wheel, and uploads it to PyPI with
`uv publish`. Authentication is PyPI
[trusted publishing](https://docs.pypi.org/trusted-publishers/) over OIDC, so there is no
PyPI token stored in this repository.

To cut a release:

```bash
# 1. bump the version in both places and commit
#      pyproject.toml            version = "0.2.0"
#      mcp_pastebin/__init__.py  __version__ = "0.2.0"
git commit -am "Release 0.2.0"

# 2. tag and push - the tag is what triggers the upload
git tag v0.2.0
git push origin main v0.2.0
```

The tag and the `version` in `pyproject.toml` must agree. PyPI never accepts a re-upload
of an existing version, so a release that fails after the upload step needs a new version
number rather than a moved tag.

### One-time PyPI setup

Before the first release, register a trusted publisher on PyPI. The project does not exist
on PyPI yet, so add it as a *pending publisher* at
<https://pypi.org/manage/account/publishing/>:

| Field | Value |
| --- | --- |
| PyPI Project Name | `mcp-pastebin` |
| Owner | `neopunisher` |
| Repository name | `py-pastebin-mcp` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

Every field is checked on upload, including the workflow filename and the
`environment: pypi` declared in `release.yml` - if you rename either, update the publisher
to match. GitHub creates the `pypi` environment on the first run; to require a manual
approval before each upload, add yourself as a required reviewer to it under
*Settings -> Environments -> pypi*.

After the first successful upload the pending publisher becomes an ordinary publisher on
the project, and no further setup is needed.

### Publishing by hand

Only needed to bypass the workflow (or to rehearse against TestPyPI):

```bash
uv build                                   # -> dist/*.whl and dist/*.tar.gz
python scripts/smoke_test.py               # start the built wheel, speak MCP to it
uv publish --token pypi-...                # upload to PyPI
uv publish --publish-url https://test.pypi.org/legacy/ --token pypi-...   # TestPyPI
```

## License

MIT
