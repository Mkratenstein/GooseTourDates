// @ts-nocheck
/**
 * Health canary: compare Seated API vs Supabase, auto-heal (upsert + Discord), retest, write canary-result.json.
 * Exit 0 only when in sync or heal+retest passed.
 */
import 'dotenv/config';
import * as fs from 'fs';
import * as path from 'path';
import { Client, GatewayIntentBits, TextChannel } from 'discord.js';
import { Scraper, Concert } from '../scraper';
import { DatabaseService } from '../database';
import { formatConcertAnnouncement, concertKey } from '../announce';
import {
    CanaryResult,
    CanaryConcertSummary,
    DiscordPostResult,
    toSummary,
} from './types';

const RESULT_PATH = path.join(process.cwd(), 'canary-result.json');

function writeResult(result: CanaryResult): void {
    fs.writeFileSync(RESULT_PATH, JSON.stringify(result, null, 2));
    console.log(`Wrote ${RESULT_PATH}`);
}

function findMissing(scraped: Concert[], saved: Concert[]): Concert[] {
    const existing = new Set(saved.map((c) => concertKey(c.venue, String(c.date))));
    return scraped
        .filter((c) => !existing.has(concertKey(c.venue, c.date)))
        .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
}

function summarize(concerts: Concert[]): CanaryConcertSummary[] {
    return concerts.map((c) => toSummary(c, concertKey(c.venue, c.date)));
}

async function checkHealthUrl(): Promise<number | null> {
    const url = process.env.HEALTH_URL;
    if (!url) return null;
    try {
        const res = await fetch(url, { signal: AbortSignal.timeout(10000) });
        return res.status;
    } catch {
        return 0;
    }
}

async function readHeartbeatAge(
    database: DatabaseService
): Promise<{ ageHours: number | null; at: string | null }> {
    const hb = await database.getHeartbeat();
    if (!hb?.last_successful_check_at) {
        return { ageHours: null, at: null };
    }
    const at = hb.last_successful_check_at;
    const ageMs = Date.now() - new Date(at).getTime();
    return { ageHours: Math.round((ageMs / 3600000) * 10) / 10, at };
}

async function postConcerts(
    concerts: Concert[]
): Promise<DiscordPostResult[]> {
    const token = process.env.DISCORD_TOKEN;
    const channelId = process.env.DISCORD_CHANNEL_ID;
    if (!token || !channelId) {
        throw new Error('DISCORD_TOKEN and DISCORD_CHANNEL_ID are required');
    }

    const client = new Client({ intents: [GatewayIntentBits.Guilds] });
    const results: DiscordPostResult[] = [];

    try {
        await client.login(token);
        await new Promise<void>((resolve, reject) => {
            const t = setTimeout(() => reject(new Error('Discord ready timeout')), 60000);
            client.once('ready', () => {
                clearTimeout(t);
                resolve();
            });
        });

        const channel = await client.channels.fetch(channelId);
        if (!channel || !(channel instanceof TextChannel)) {
            throw new Error(`Channel ${channelId} not found or not a text channel`);
        }

        for (const concert of concerts) {
            try {
                await channel.send(formatConcertAnnouncement(concert));
                results.push({
                    id: concert.id,
                    date: concert.date,
                    venue: concert.venue,
                    discordOk: true,
                });
                console.log(`Canary: posted ${concert.date} ${concert.venue}`);
            } catch (e) {
                results.push({
                    id: concert.id,
                    date: concert.date,
                    venue: concert.venue,
                    discordOk: false,
                    discordError: String(e?.message || e),
                });
            }
        }
    } finally {
        client.destroy();
    }

    return results;
}

async function main(): Promise<void> {
    const base: Partial<CanaryResult> = {
        timestamp: new Date().toISOString(),
        scrapedCount: 0,
        savedCount: 0,
        missingBefore: [],
        missingAfter: [],
        discordPosts: [],
        heartbeatAgeHours: null,
        heartbeatAt: null,
        healthUrlStatus: null,
        runUrl: process.env.GITHUB_RUN_URL || undefined,
    };

    const scraper = new Scraper();
    const database = new DatabaseService();

    try {
        await scraper.initialize();
        base.healthUrlStatus = await checkHealthUrl();
        const hb = await readHeartbeatAge(database);
        base.heartbeatAgeHours = hb.ageHours;
        base.heartbeatAt = hb.at;

        let scraped: Concert[];
        try {
            scraped = await scraper.scrapeTourDates();
        } catch (e) {
            const result: CanaryResult = {
                ...base,
                outcome: 'hard_error',
                stage: 'scrape',
                exitCode: 1,
                message: 'Failed to fetch Seated tour API',
                error: String(e?.message || e),
            } as CanaryResult;
            writeResult(result);
            process.exit(1);
        }

        if (!scraped.length) {
            const result: CanaryResult = {
                ...base,
                outcome: 'hard_error',
                stage: 'scrape',
                exitCode: 1,
                message: 'Seated API returned zero tour events',
                scrapedCount: 0,
            } as CanaryResult;
            writeResult(result);
            process.exit(1);
        }

        base.scrapedCount = scraped.length;

        let saved: Concert[];
        try {
            saved = await database.getConcerts();
        } catch (e) {
            const result: CanaryResult = {
                ...base,
                outcome: 'hard_error',
                stage: 'diff',
                exitCode: 1,
                message: 'Failed to read concerts from Supabase',
                error: String(e?.message || e),
            } as CanaryResult;
            writeResult(result);
            process.exit(1);
        }

        base.savedCount = saved.length;
        const missing = findMissing(scraped, saved);
        base.missingBefore = summarize(missing);

        if (missing.length === 0) {
            const result: CanaryResult = {
                ...base,
                outcome: 'in_sync',
                stage: 'ok',
                exitCode: 0,
                message: 'Seated and Supabase are in sync; no remediation needed',
                missingAfter: [],
            } as CanaryResult;
            writeResult(result);
            process.exit(0);
        }

        console.log(`Canary: ${missing.length} missing concert(s); remediating.`);

        try {
            await database.saveConcerts(missing);
        } catch (e) {
            const result: CanaryResult = {
                ...base,
                outcome: 'heal_failed',
                stage: 'upsert',
                exitCode: 1,
                message: 'Failed to upsert missing concerts to Supabase',
                error: String(e?.message || e),
            } as CanaryResult;
            writeResult(result);
            process.exit(1);
        }

        let discordPosts: DiscordPostResult[];
        try {
            discordPosts = await postConcerts(missing);
        } catch (e) {
            const result: CanaryResult = {
                ...base,
                outcome: 'heal_failed',
                stage: 'discord',
                exitCode: 1,
                message: 'Failed to connect or post to Discord',
                error: String(e?.message || e),
                discordPosts: [],
            } as CanaryResult;
            writeResult(result);
            process.exit(1);
        }

        base.discordPosts = discordPosts;
        const discordFailed = discordPosts.filter((p) => !p.discordOk);

        // Immediate retest
        let savedAfter: Concert[];
        try {
            savedAfter = await database.getConcerts();
        } catch (e) {
            const result: CanaryResult = {
                ...base,
                outcome: 'heal_failed',
                stage: 'retest',
                exitCode: 1,
                message: 'Heal completed but retest could not re-read Supabase',
                error: String(e?.message || e),
            } as CanaryResult;
            writeResult(result);
            process.exit(1);
        }

        const missingAfter = findMissing(scraped, savedAfter);
        base.missingAfter = summarize(missingAfter);
        base.savedCount = savedAfter.length;

        const idsStillMissing = missing
            .filter((c) => !savedAfter.some((s) => s.id === c.id))
            .map((c) => c.id);

        if (missingAfter.length > 0 || idsStillMissing.length > 0 || discordFailed.length > 0) {
            const parts: string[] = [];
            if (missingAfter.length > 0) {
                parts.push(`${missingAfter.length} still missing from DB after upsert`);
            }
            if (discordFailed.length > 0) {
                parts.push(`${discordFailed.length} Discord post(s) failed`);
            }
            const result: CanaryResult = {
                ...base,
                outcome: 'heal_failed',
                stage: 'retest',
                exitCode: 1,
                message: `Retest failed: ${parts.join('; ')}`,
            } as CanaryResult;
            writeResult(result);
            process.exit(1);
        }

        const result: CanaryResult = {
            ...base,
            outcome: 'healed',
            stage: 'ok',
            exitCode: 0,
            message: `Auto-healed ${missing.length} concert(s); retest passed`,
            missingAfter: [],
        } as CanaryResult;
        writeResult(result);
        process.exit(0);
    } catch (e) {
        const result: CanaryResult = {
            ...base,
            outcome: 'hard_error',
            stage: 'diff',
            exitCode: 1,
            message: 'Unexpected canary failure',
            error: String(e?.message || e),
            scrapedCount: base.scrapedCount || 0,
            savedCount: base.savedCount || 0,
            missingBefore: base.missingBefore || [],
            missingAfter: base.missingAfter || [],
            discordPosts: base.discordPosts || [],
            heartbeatAgeHours: base.heartbeatAgeHours ?? null,
            heartbeatAt: base.heartbeatAt ?? null,
            healthUrlStatus: base.healthUrlStatus ?? null,
            timestamp: new Date().toISOString(),
        };
        writeResult(result);
        process.exit(1);
    } finally {
        await scraper.close().catch(() => {});
    }
}

main();
