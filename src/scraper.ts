import puppeteer, { Browser } from 'puppeteer';

export interface Concert {
    venue: string;
    location: string;
    date: string;
}

export class Scraper {
    private browser: Browser | null = null;
    private readonly url = 'https://www.goosetheband.com/tour';

    private async initialize(): Promise<void> {
        this.browser = await puppeteer.launch({
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox'],
        });
    }

    public async scrapeTourDates(): Promise<Concert[]> {
        if (!this.browser) {
            await this.initialize();
        }

        const page = await this.browser!.newPage();
        await page.goto(this.url, { waitUntil: 'networkidle2' });

        const concerts = await page.evaluate(() => {
            const concertElements = document.querySelectorAll('.shows-list-item');
            const concertData: Concert[] = [];

            concertElements.forEach(element => {
                const venue = element.querySelector('.show-venue a')?.textContent?.trim() ?? '';
                const location = element.querySelector('.show-location')?.textContent?.trim() ?? '';
                const date = element.querySelector('.show-date-short')?.textContent?.trim() ?? '';
                
                if (venue && location && date) {
                    concertData.push({ venue, location, date });
                }
            });

            return concertData;
        });
        
        await page.close();
        return concerts;
    }

    public async close(): Promise<void> {
        if (this.browser) {
            await this.browser.close();
        }
    }
} 