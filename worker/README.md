# Orchestra worker

A disposable implementer node. It runs the webhook receiver + a cloudflared
quick tunnel, points a GitHub push webhook at itself, and on a dispatch request
runs the implementer steps through `scripts/dispatch.py` and pushes the result
branch back. The audit gate stays on the orchestrator — see
[../docs/distributed.md](../docs/distributed.md).

## Paste this into the worker machine's agent

```
Set up an orchestra worker on this machine:

  git clone https://github.com/khangpworking/model-orchestra ~/model-orchestra 2>/dev/null \
    || git -C ~/model-orchestra pull
  REPO=khangpworking/model-orchestra bash ~/model-orchestra/worker/setup.sh

If it reports a missing tool, install it and re-run the last line.
If it says to run `gh auth login`, do that (scopes: repo, admin:repo_hook), then re-run.
When it prints "Worker up", send me the tunnel URL it shows.
```

## Prerequisites the script cannot do for you

- **`gh auth login`** — one-time, needs a browser (OAuth). Scopes: `repo`,
  `admin:repo_hook`.
- **Model access for `pi`** — `dispatch.py` calls `pi --provider cliproxy`.
  `pi` on this machine must have a reachable provider configured. If this box
  has no local cliproxy, set `PI_PROVIDER`/`PI_MODEL` to something it can reach
  before running setup.

## Dispatch protocol

The orchestrator triggers a run by committing `.ai/DISPATCH.md` on a feature
branch and pushing:

```
branch: feat/<feature>
steps: 4,5
status: requested
```

The receiver acts only on `status: requested`, sets it to `running`, runs the
steps, then sets `done` or `failed` and pushes — so its own pushes never
re-trigger it.

## Teardown

```
pkill -f receiver.py
pkill -f 'cloudflared tunnel --url'
```

Then delete the webhook from the repo's Settings → Webhooks (or
`gh api -X DELETE repos/<owner>/<repo>/hooks/<id>`). Nothing else persists.
