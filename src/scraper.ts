import puppeteer, { Browser } from 'puppeteer';

export interface Concert {
    venue: string;
    location: string;
    date: string;
}

export class Scraper {
    private browser: Browser | null = null;
    private readonly url = 'https://www.songkick.com/artists/4219891-goose/calendar';

    public async initialize(): Promise<void> {
        if (this.browser) {
            console.log('Scraper: Browser is already initialized.');
            return;
        }
        console.log('Scraper: Initializing browser.');
        this.browser = await puppeteer.launch({
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox'],
        });
    }

    public async scrapeTourDates(): Promise<Concert[]> {
        if (!this.browser) {
            throw new Error('Scraper not initialized. Call initialize() before scraping.');
        }

        console.log('Scraper: Starting to scrape tour dates.');
        const page = await this.browser.newPage();
        await page.goto(this.url, { waitUntil: 'networkidle2' });

        try {
            await page.waitForSelector('.event-listings-element', { timeout: 15000 });
            console.log('Scraper: Found concert list container on Songkick.');
        } catch (error) {
            console.error('Scraper: Could not find concert list container on Songkick. The website structure may have changed.');
            await page.close();
            return [];
        }

        const concerts = await page.evaluate(() => {
            const concertElements = document.querySelectorAll('.event-listings-element');
            const concertData: Concert[] = [];

            concertElements.forEach(element => {
                const date = element.querySelector('time')?.textContent?.trim() ?? '';
                const venue = element.querySelector('.venue-name a')?.textContent?.trim() ?? '';
                const location = element.querySelector('.location-and-datetime-container .location span:last-child')?.textContent?.trim() ?? '';
                
                if (venue && location && date) {
                    concertData.push({ venue, location, date });
                }
            });

            return concertData;
        });
        
        console.log(`Scraper: Found ${concerts.length} concerts on the page.`);
        await page.close();
        return concerts;
    }

    public async close(): Promise<void> {
        if (this.browser) {
            console.log('Scraper: Closing browser.');
            await this.browser.close();
            this.browser = null;
        }
    }
} 