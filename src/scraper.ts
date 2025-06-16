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

        // Set a user agent to avoid basic bot detection
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36');

        await page.goto(this.url, { waitUntil: 'networkidle2' });

        try {
            // Handle cookie consent banners
            const acceptButton = await page.$('button.accept-all, button#accept-cookies');
            if (acceptButton) {
                console.log('Scraper: Found and clicked the cookie consent button.');
                await acceptButton.click();
                await page.waitForNavigation({ waitUntil: 'networkidle2' });
            }
        } catch (error) {
            console.log('Scraper: Did not find a cookie consent button, or it was not clickable. Continuing...');
        }
        
        try {
            // Wait for the main container of the event listings
            await page.waitForSelector('li.event-listing', { timeout: 15000 });
            console.log('Scraper: Found concert list container on Songkick.');
        } catch (error) {
            console.error('Scraper: Could not find concert list container on Songkick. The website structure may have changed.');
            
            // Log the full page content for debugging
            const pageContent = await page.content();
            console.error('Scraper: Full page HTML:', pageContent);

            await page.close();
            return [];
        }

        const concerts = await page.evaluate(() => {
            const concertElements = document.querySelectorAll('li.event-listing');
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