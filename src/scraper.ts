export interface Concert {
    venue: string;
    location: string;
    date: string;
}

interface SeatedTourEvent {
    attributes: {
        'starts-at-short': string;
        'venue-name': string;
        'formatted-address': string;
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
                        date: attributes['starts-at-short'],
                        venue: attributes['venue-name'],
                        location: attributes['formatted-address'],
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