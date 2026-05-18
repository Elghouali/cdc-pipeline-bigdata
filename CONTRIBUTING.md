# Contributing to the CDC Pipeline

Thanks for contributing. This guide covers everything you need to get a local
environment running, follow our conventions, and land a clean pull request.

---

## Prerequisites

Install the following before you start:

| Tool             | Version   | Purpose                                      |
|------------------|-----------|----------------------------------------------|
| Docker + Compose | 24+       | Runs the full pipeline stack                 |
| GNU Make         | 4+        | Task runner for every workflow               |
| Node.js          | 20.x LTS  | Frontend build, lint, and tests              |
| Python           | 3.11      | API, Spark jobs, linting, and tests          |
| Git              | 2.40+     | Version control                              |

Optional but recommended:

- `pre-commit` — `pip install pre-commit`
- `ruff` — `pip install ruff`
- `shellcheck` — `apt-get install shellcheck` / `brew install shellcheck`

---

## Local Setup

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd cdc-pipeline

# 2. Create your environment file from the template
cp .env.example .env
#    Edit .env if you need non-default credentials or ports.

# 3. Start the full stack (renders configs + docker compose up)
make up

# 4. Run the end-to-end pipeline in one command
#    (registers the Debezium connector, submits Spark jobs, starts the simulator)
make pipeline-start
```

Useful service endpoints once the stack is healthy:

- Frontend — http://localhost:3000
- API — http://localhost:8000
- Trino UI — http://localhost:8080
- Spark Master UI — http://localhost:8085
- MinIO Console — http://localhost:9001
- Superset — http://localhost:8088
- Grafana — http://localhost:3001
- Kafka Connect — http://localhost:8083

Tear down with `make down` (keeps volumes) or `make reset` (deletes all data).

---

## Branch Naming Convention

Create a feature branch off `main`. Never commit directly to `main`
(the `no-commit-to-branch` pre-commit hook enforces this).

| Prefix      | Use for                                        |
|-------------|-------------------------------------------------|
| `feat/`     | New features                                    |
| `fix/`      | Bug fixes                                       |
| `chore/`    | Tooling, deps, CI, non-functional housekeeping  |
| `refactor/` | Code restructuring with no behavior change      |

Examples:

```
feat/gold-layer-aggregations
fix/debezium-connector-retry
chore/bump-ruff-version
refactor/silver-job-schema-handling
```

---

## Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <short imperative description>

<optional body explaining the why>
```

Allowed types: `feat`, `fix`, `chore`, `refactor`, `docs`, `test`, `perf`, `ci`.

Examples:

```
feat: add gold-layer daily revenue aggregation
fix: handle null payloads in silver job
docs: document connector registration steps
ci: add detect-secrets scan to the CI workflow
```

Keep the subject line under ~72 characters and written in the imperative mood
("add", not "added" or "adds").

---

## Running Tests

Run the full suite (Python + frontend + shell):

```bash
make test
```

Run a single layer:

```bash
make test-python      # API pytest suite
make test-frontend    # Frontend Vitest suite
make test-shell       # shellcheck on scripts/
make test-e2e         # Playwright end-to-end tests
```

Lint everything:

```bash
make lint             # ruff + eslint + shellcheck
```

---

## Pre-commit Hooks

Install the git hooks once, then they run automatically on every commit:

```bash
pip install pre-commit
pre-commit install
```

Run all hooks against the whole repo at any time:

```bash
pre-commit run --all-files
```

The configured hooks (see `.pre-commit-config.yaml`):

- Whitespace / end-of-file / YAML / JSON / merge-conflict checks
- Private-key and secret detection (`detect-secrets` against `.secrets.baseline`)
- `ruff` lint + format for `spark_jobs/` and `api/`
- `shellcheck` for `scripts/`
- Blocks direct commits to `main`

If `detect-secrets` flags a false positive, audit and update the baseline:

```bash
detect-secrets scan --baseline .secrets.baseline
detect-secrets audit .secrets.baseline
```

---

## Pull Request Checklist

Before opening a PR, confirm:

- [ ] Branch follows the naming convention and targets `main`
- [ ] Commits follow Conventional Commits
- [ ] `make test` passes locally
- [ ] `make lint` reports no errors
- [ ] `pre-commit run --all-files` passes
- [ ] No secrets, credentials, or `.env` files are committed
- [ ] New behavior is covered by tests
- [ ] Documentation updated when behavior or setup changed

CI runs lint, tests, and a secret scan on every PR. The integration workflow
can be triggered manually from the Actions tab when stack-level changes need
verification. A PR is ready to merge once all required checks are green and it
has at least one approving review.

---

## Getting Help

- Check `README.md` for an architecture overview.
- Run `make help` to list every available task.
- Open a GitHub issue for bugs or proposals before large changes.
