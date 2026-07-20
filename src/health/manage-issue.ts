// @ts-nocheck
/**
 * Manage the sticky GitHub Issue for the health canary from canary-result.json.
 * Uses GITHUB_TOKEN + GitHub REST API (no extra deps).
 */
import * as fs from 'fs';
import * as path from 'path';
import { CanaryResult } from './types';

const RESULT_PATH = path.join(process.cwd(), 'canary-result.json');
const LABEL = 'health-canary';
const LABEL_MANUAL = 'needs-manual';
const TITLE = 'Tour sync canary';
const TITLE_ESCALATED = '[ESCALATED] Tour sync canary';
const FAIL_MARKER_RE = /<!--\s*canary-fail-count:(\d+)\s*-->/;

interface GhIssue {
    number: number;
    title: string;
    body: string | null;
    state: string;
    html_url: string;
}

function requireEnv(name: string): string {
    const v = process.env[name];
    if (!v) throw new Error(`${name} is required`);
    return v;
}

async function gh(
    method: string,
    apiPath: string,
    body?: unknown
): Promise<any> {
    const token = requireEnv('GITHUB_TOKEN');
    const res = await fetch(`https://api.github.com${apiPath}`, {
        method,
        headers: {
            Accept: 'application/vnd.github+json',
            Authorization: `Bearer ${token}`,
            'X-GitHub-Api-Version': '2022-11-28',
            'Content-Type': 'application/json',
        },
        body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`GitHub API ${method} ${apiPath} failed: ${res.status} ${text}`);
    }
    if (res.status === 204) return null;
    return res.json();
}

async function ensureLabel(owner: string, repo: string, name: string, color: string, description: string) {
    const res = await fetch(`https://api.github.com/repos/${owner}/${repo}/labels/${encodeURIComponent(name)}`, {
        headers: {
            Accept: 'application/vnd.github+json',
            Authorization: `Bearer ${requireEnv('GITHUB_TOKEN')}`,
            'X-GitHub-Api-Version': '2022-11-28',
        },
    });
    if (res.status === 404) {
        await gh('POST', `/repos/${owner}/${repo}/labels`, { name, color, description });
    }
}

async function findOpenCanaryIssue(owner: string, repo: string): Promise<GhIssue | null> {
    const issues: GhIssue[] = await gh(
        'GET',
        `/repos/${owner}/${repo}/issues?state=open&labels=${encodeURIComponent(LABEL)}&per_page=20`
    );
    const onlyIssues = issues.filter((i: any) => !i.pull_request);
    return onlyIssues.find((i) => i.title === TITLE || i.title === TITLE_ESCALATED) || onlyIssues[0] || null;
}

function runbookMarkdown(): string {
    return [
        '### Manual runbook',
        '1. Open the linked Actions run logs; confirm which stage failed.',
        '2. Re-run **workflow_dispatch** on `health-canary`.',
        '3. Verify GitHub secrets match Railway (`SUPABASE_*`, `DISCORD_*`).',
        '4. In Supabase: confirm `concerts` readable/writable; check for grant/RLS errors (42501).',
        '5. Hit Railway `/health` (or `HEALTH_URL`); check Railway deploy/logs.',
        '6. If DB fixed but Discord failed: use `/postbydate YYYY-MM-DD` or fix token/channel and re-run.',
        '7. If Seated is down: wait; do not mass-post guesses.',
        '',
        'See `docs/health-canary.md` in the repo.',
    ].join('\n');
}

function formatMissingList(items: CanaryResult['missingBefore']): string {
    if (!items.length) return '_None_';
    return items
        .map(
            (c) =>
                `- \`${c.date}\` **${c.venue}** (${c.location})${c.details ? ` — ${c.details}` : ''} — [tickets](https://link.seated.com/${c.id})`
        )
        .join('\n');
}

function buildBody(result: CanaryResult, failCount: number, previousBody?: string | null): string {
    const marker = `<!-- canary-fail-count:${failCount} -->`;
    const lines = [
        marker,
        '',
        `**Outcome:** \`${result.outcome}\`  `,
        `**Stage:** \`${result.stage}\`  `,
        `**Message:** ${result.message}  `,
        `**When:** ${result.timestamp}`,
        '',
        '| Metric | Value |',
        '| --- | --- |',
        `| Scraped (Seated) | ${result.scrapedCount} |`,
        `| In Supabase | ${result.savedCount} |`,
        `| Missing before heal | ${result.missingBefore.length} |`,
        `| Missing after retest | ${result.missingAfter.length} |`,
        `| Bot heartbeat age (h) | ${result.heartbeatAgeHours ?? 'n/a'} |`,
        `| Heartbeat at | ${result.heartbeatAt ?? 'n/a'} |`,
        `| HEALTH_URL status | ${result.healthUrlStatus ?? 'n/a'} |`,
        '',
    ];

    if (result.runUrl) {
        lines.push(`**Actions run:** ${result.runUrl}`, '');
    }
    if (result.error) {
        lines.push(`**Error:** \`${result.error.replace(/`/g, "'")}\``, '');
    }

    lines.push('### Missing before remediation', formatMissingList(result.missingBefore), '');
    if (result.missingAfter.length) {
        lines.push('### Still missing after retest', formatMissingList(result.missingAfter), '');
    }
    if (result.discordPosts.length) {
        lines.push('### Discord posts');
        for (const p of result.discordPosts) {
            lines.push(
                `- ${p.discordOk ? 'OK' : 'FAIL'} \`${p.date}\` ${p.venue}${p.discordError ? ` — ${p.discordError}` : ''}`
            );
        }
        lines.push('');
    }

    if (result.exitCode !== 0) {
        lines.push(runbookMarkdown(), '');
    }

    return lines.join('\n');
}

function readFailCount(body: string | null | undefined): number {
    if (!body) return 0;
    const m = body.match(FAIL_MARKER_RE);
    return m ? parseInt(m[1], 10) : 0;
}

async function main(): Promise<void> {
    if (!fs.existsSync(RESULT_PATH)) {
        throw new Error(`Missing ${RESULT_PATH}; run the canary first`);
    }
    const result: CanaryResult = JSON.parse(fs.readFileSync(RESULT_PATH, 'utf8'));
    const repoFull = requireEnv('GITHUB_REPOSITORY'); // owner/repo
    const [owner, repo] = repoFull.split('/');

    await ensureLabel(owner, repo, LABEL, 'd93f0b', 'Tour sync health canary');
    await ensureLabel(owner, repo, LABEL_MANUAL, 'b60205', 'Canary needs manual intervention');

    let issue = await findOpenCanaryIssue(owner, repo);
    const prevFail = issue ? readFailCount(issue.body) : 0;

    if (result.outcome === 'in_sync' || result.outcome === 'healed') {
        const body = buildBody(result, 0);
        const comment =
            result.outcome === 'in_sync'
                ? `## Healthy / no drift\n\n${body}`
                : `## Auto-healed and retest passed\n\n${body}`;

        if (issue) {
            await gh('POST', `/repos/${owner}/${repo}/issues/${issue.number}/comments`, { body: comment });
            await gh('PATCH', `/repos/${owner}/${repo}/issues/${issue.number}`, {
                state: 'closed',
                title: TITLE,
                labels: [LABEL],
            });
            console.log(`Closed issue #${issue.number}`);
        } else if (result.outcome === 'healed') {
            // Audit trail for a heal that had no prior open issue: open then close.
            const created: GhIssue = await gh('POST', `/repos/${owner}/${repo}/issues`, {
                title: TITLE,
                body,
                labels: [LABEL],
            });
            await gh('POST', `/repos/${owner}/${repo}/issues/${created.number}/comments`, {
                body: '## Auto-healed and retest passed\n\nClosing after verified remediation.',
            });
            await gh('PATCH', `/repos/${owner}/${repo}/issues/${created.number}`, { state: 'closed' });
            console.log(`Opened and closed audit issue #${created.number}`);
        } else {
            console.log('In sync; no open canary issue to close.');
        }
        return;
    }

    // Failure path
    const failCount = prevFail + 1;
    const escalate = failCount >= 2;
    const title = escalate ? TITLE_ESCALATED : TITLE;
    const labels = escalate ? [LABEL, LABEL_MANUAL] : [LABEL];
    const body = buildBody(result, failCount, issue?.body);
    const comment = `## Canary failure (attempt ${failCount})\n\n${body}`;

    if (issue) {
        await gh('POST', `/repos/${owner}/${repo}/issues/${issue.number}/comments`, { body: comment });
        await gh('PATCH', `/repos/${owner}/${repo}/issues/${issue.number}`, {
            title,
            body,
            labels,
            state: 'open',
        });
        console.log(`Updated open issue #${issue.number} (failCount=${failCount})`);
    } else {
        const created: GhIssue = await gh('POST', `/repos/${owner}/${repo}/issues`, {
            title,
            body,
            labels,
        });
        console.log(`Opened issue #${created.number}`);
    }
}

main().catch((e) => {
    console.error(e);
    process.exit(1);
});
