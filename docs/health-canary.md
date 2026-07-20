# Tour Health Canary

Scheduled GitHub Action that compares the live [Seated](https://cdn.seated.com) tour API to Supabase, auto-heals drift (upsert + Discord post), immediately retests, and manages a sticky GitHub Issue.

## Schedule

| Job | Cron | When |
| --- | --- | --- |
| Railway bot (`src/bot.ts`) | `0 */4 * * *` | Top of every 4th hour |
| Health canary (Actions) | `30 */4 * * *` | 30 minutes past every 4th hour |

Manual run: **Actions → Health Canary → Run workflow**.

## Required GitHub secrets

Repo → **Settings → Secrets and variables → Actions**:

| Secret | Required | Purpose |
| --- | --- | --- |
| `SUPABASE_URL` | Yes | Same as Railway |
| `SUPABASE_KEY` | Yes | Same as Railway (service role or key that can read/write `concerts`) |
| `DISCORD_TOKEN` | Yes | Bot token used to post announcements |
| `DISCORD_CHANNEL_ID` | Yes | Tour announcement channel |
| `HEALTH_URL` | No | Full URL to Railway `/health` (e.g. `https://your-app.up.railway.app/health`) |

`GITHUB_TOKEN` is provided automatically (workflow has `issues: write`).

## One-time Supabase: `bot_heartbeat` table

Run in the Supabase SQL editor (adjust grants if your key is not `service_role`):

```sql
create table if not exists public.bot_heartbeat (
  id int primary key default 1 check (id = 1),
  last_successful_check_at timestamptz not null default now()
);

insert into public.bot_heartbeat (id, last_successful_check_at)
values (1, now())
on conflict (id) do nothing;

-- If using the anon/authenticated roles for the Data API key:
grant select, insert, update on public.bot_heartbeat to anon, authenticated, service_role;
```

The Railway bot writes this row after each successful `checkTours`. The canary reports heartbeat age on Issues; missing table only logs an error and does not fail the scrape.

## What the canary does

1. Fetch Seated tour events  
2. Fetch all Supabase `concerts` (paginated)  
3. Diff by `venue.trim()|YYYY-MM-DD`  
4. If missing: upsert → post Discord (same message format as the bot) → **retest** (re-read DB; missing set must be empty; all Discord sends OK)  
5. Write `canary-result.json`  
6. Manage sticky Issue labeled `health-canary`

### Issue close / failure rules

| Outcome | Issue |
| --- | --- |
| In sync | Comment + **close** if open |
| Healed + retest pass | Comment + **close** (or open-then-close for audit) |
| Heal/retest/hard failure | Keep **open**; fail the workflow; next cron retries |
| 2+ consecutive failures | Title `[ESCALATED] Tour sync canary` + label `needs-manual` |

## Manual runbook (when escalated)

1. Open the linked Actions run logs; confirm stage (`scrape` / `upsert` / `discord` / `retest`).  
2. Re-run **workflow_dispatch** on Health Canary.  
3. Verify secrets match Railway.  
4. In Supabase: grants/RLS on `concerts` (and `bot_heartbeat`).  
5. Check Railway `/health` and bot logs.  
6. If DB OK but Discord failed: `/postbydate YYYY-MM-DD` (admin) or fix token/channel.  
7. If Seated is down: wait; do not invent shows.

## Local commands

```bash
npx ts-node src/health/canary.ts
# then, with GITHUB_TOKEN + GITHUB_REPOSITORY=owner/repo:
npx ts-node src/health/manage-issue.ts
```

Or: `npm run canary` then `npm run canary:issue`.
