# Goose Tour Dates

A TypeScript Discord bot that watches [Goose](https://goosetheband.com) tour dates, stores them in Supabase, and posts new shows to a Discord channel.

The bot reads the official Seated tour API (no browser scraping), deduplicates by venue + date, and announces new dates automatically. It runs on Railway. A scheduled GitHub Actions canary re-checks the same data and heals drift if a show was missed.

## What it does

- Fetches tour events from the Seated API every 4 hours
- Upserts new concerts into Supabase (`concerts` table)
- Posts Discord announcements with date, venue, location, optional details, and a ticket link
- Writes a heartbeat after each successful check (`bot_heartbeat` table)
- Exposes `/health` for Railway and the canary

Example announcement:

```
Goose the Organization has announced a new show!

September 4, 2026
Venue Name | City, ST
optional details

🎫 tickets: https://link.seated.com/<event-id>
```

## Discord commands

| Command | Who | What |
| --- | --- | --- |
| `/scrape` | Anyone in the server | Kick off a tour check and post a status reply in the channel |
| `/status` | Anyone in the server | Confirm the bot is running |
| `/postbydate` | Admin role only | Re-post stored concerts for a date (`YYYY-MM-DD`) |

`/scrape` replies immediately, then runs the job in the background through an internal HTTP endpoint so Discord interactions do not time out.

## Architecture

```
Seated tour API
      │
      ▼
src/scraper.ts  ──►  src/database.ts (Supabase)
      │                      │
      ▼                      ▼
src/announce.ts         concerts + bot_heartbeat
      │
      ▼
Discord channel  ◄──  src/bot.ts (Railway, cron every 4h)
                          │
                          └── GET /health, POST /scrape-job

GitHub Actions (30 min after each bot cron)
  src/health/canary.ts  →  upsert + Discord if missing  →  sticky Issue
```

| Piece | Role |
| --- | --- |
| `src/index.ts` | Process entrypoint, graceful shutdown |
| `src/bot.ts` | Discord client, slash commands, cron, HTTP server |
| `src/scraper.ts` | Seated API client |
| `src/database.ts` | Supabase reads/writes (paginated concert fetch, upsert) |
| `src/announce.ts` | Shared announcement text and duplicate keys |
| `src/health/` | Independent canary + GitHub Issue manager |

New vs existing shows are compared with `venue.trim()|YYYY-MM-DD`. Saves use `upsert` on concert `id` so re-runs do not create duplicates.

## Requirements

- Node.js 20+
- A Discord bot token and a text channel ID
- A Supabase project with `concerts` and `bot_heartbeat` tables
- For production: a Railway service (or any host that can keep a Node process running)

## Setup

1. Clone and install:

```bash
git clone https://github.com/Mkratenstein/GooseTourDates.git
cd GooseTourDates
npm install
```

2. Create a `.env` file (never commit this file):

```
DISCORD_TOKEN=your_bot_token
DISCORD_CHANNEL_ID=your_channel_id
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_key
PORT=8080
```

Optional, used by the health canary:

```
HEALTH_URL=https://your-app.up.railway.app/health
```

3. Invite the bot to your Discord server with permissions to send messages and use slash commands.

4. Run locally:

```bash
npm run dev
```

Production start (TypeScript compile, then Node):

```bash
npm start
```

## Scripts

| Script | Purpose |
| --- | --- |
| `npm run dev` | Watch `src/` and run with `ts-node` |
| `npm start` | Build to `dist/` and run `dist/index.js` |
| `npm run build` | TypeScript compile only |
| `npm run canary` | Run the tour-sync health canary locally |
| `npm run canary:issue` | Update the sticky GitHub Issue from `canary-result.json` |

## Health canary

GitHub Actions runs **Health Canary** at `:30` past every 4th hour (offset from the bot’s `:00` cron to reduce double-posts). It:

1. Compares Seated vs Supabase
2. Upserts and posts any missing shows
3. Retests immediately
4. Opens, comments on, or closes a sticky Issue labeled `health-canary`

Manual run: **Actions → Health Canary → Run workflow**.

Full secrets list, SQL for `bot_heartbeat`, failure/escalation rules, and the runbook live in [docs/health-canary.md](docs/health-canary.md).

## Environment variables

| Variable | Used by | Required |
| --- | --- | --- |
| `DISCORD_TOKEN` | Bot and canary | Yes |
| `DISCORD_CHANNEL_ID` | Bot and canary | Yes |
| `SUPABASE_URL` | Bot and canary | Yes |
| `SUPABASE_KEY` | Bot and canary | Yes |
| `PORT` | Bot HTTP server | No (defaults to `8080`) |
| `HEALTH_URL` | Canary | No |
| `GITHUB_TOKEN` | Canary issue manager | Provided in Actions |

## CI

- **Health Canary** — scheduled tour-sync check (see above)
- **CodeQL** — JavaScript/TypeScript analysis on `master` and PRs

## License

ISC. See `package.json`.
