// @ts-nocheck
import { Concert } from '../scraper';

export type CanaryStage =
    | 'scrape'
    | 'diff'
    | 'upsert'
    | 'discord'
    | 'retest'
    | 'health'
    | 'ok';

export type CanaryOutcome =
    | 'in_sync'
    | 'healed'
    | 'heal_failed'
    | 'hard_error';

export interface DiscordPostResult {
    id: string;
    date: string;
    venue: string;
    discordOk: boolean;
    discordError?: string;
}

export interface CanaryConcertSummary {
    id: string;
    date: string;
    venue: string;
    location: string;
    details?: string;
    key: string;
}

export interface CanaryResult {
    timestamp: string;
    outcome: CanaryOutcome;
    stage: CanaryStage;
    exitCode: 0 | 1;
    message: string;
    scrapedCount: number;
    savedCount: number;
    missingBefore: CanaryConcertSummary[];
    missingAfter: CanaryConcertSummary[];
    discordPosts: DiscordPostResult[];
    heartbeatAgeHours: number | null;
    heartbeatAt: string | null;
    healthUrlStatus: number | null;
    error?: string;
    runUrl?: string;
}

export function toSummary(c: Concert, key: string): CanaryConcertSummary {
    return {
        id: c.id,
        date: c.date,
        venue: c.venue,
        location: c.location,
        details: c.details,
        key,
    };
}
