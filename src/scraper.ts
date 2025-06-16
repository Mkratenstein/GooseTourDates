// @ts-nocheck
export interface Concert {
    id: string; // For the ticket link
    venue: string;
    location: string;
    date: string; // This is the YYYY-MM-DD date
    details?: string; // Optional, for "Goose & Mt. Joy"
}

interface SeatedTourEvent {
    id: string;
    attributes: {
        'starts-at-date-local': string;
        'venue-name': string;
        'formatted-address': string;
        details: string | null;
    };
    type: string;
}

export class Scraper {
    private readonly url = 'https://cdn.seated.com/api/tour/fe8f12bb-393b-4746-a9c3-11b276c68b5d?include=tour-events';

    public async initialize(): Promise<void> {
        // No browser initialization needed anymore
        console.log('Scraper initialized (API mode).');
    }

    public async scrapeTourDates(): Promise<Concert[]> {
        console.log('Scraper: Fetching tour dates from Seated API.');
        
        try {
            const response = await fetch(this.url);
            if (!response.ok) {
                throw new Error(`API request failed with status ${response.status}: ${await response.text()}`);
            }
            
            const jsonData = await response.json() as { included: SeatedTourEvent[] };

            if (!jsonData.included || !Array.isArray(jsonData.included)) {
                console.error('Scraper: Invalid data structure from API. "included" array not found.');
                return [];
            }

            const concerts: Concert[] = jsonData.included
                .filter(event => event.type === 'tour-events' && event.attributes)
                .map(event => {
                    const attributes = event.attributes;
                    return {
                        id: event.id,
                        date: attributes['starts-at-date-local'],
                        venue: attributes['venue-name'],
                        location: attributes['formatted-address'],
                        details: attributes.details || undefined,
                    };
                });
            
            console.log(`Scraper: Found ${concerts.length} concerts via API.`);
            return concerts;

        } catch (error) {
            console.error('Scraper: Error fetching or parsing tour data from API.', error);
            return [];
        }
    }

    public async close(): Promise<void> {
        // No browser to close
        console.log('Scraper closed (API mode).');
    }
} 