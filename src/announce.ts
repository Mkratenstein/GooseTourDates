// @ts-nocheck
import { Concert } from './scraper';

/** Same announcement text used by the Discord bot and the health canary. */
export function formatConcertAnnouncement(concert: Concert): string {
    const date = new Date(`${concert.date}T12:00:00Z`);
    const formattedDate = date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        timeZone: 'UTC',
    });

    const messageParts = [
        'Goose the Organization has announced a new show!',
        '',
        formattedDate,
        `${(concert.venue || '').trim()} | ${concert.location}`,
    ];

    if (concert.details) {
        messageParts.push(concert.details);
    }

    messageParts.push('');
    messageParts.push(`🎫 tickets: https://link.seated.com/${concert.id}`);

    return messageParts.join('\n');
}

export function concertKey(venue: string, date: string): string {
    const datePart = date.includes('T')
        ? new Date(date).toISOString().split('T')[0]
        : date;
    return `${(venue || '').trim()}|${datePart}`;
}
