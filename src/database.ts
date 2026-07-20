// @ts-nocheck
import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { Concert } from './scraper';

export class DatabaseService {
    private client: SupabaseClient;

    constructor() {
        const supabaseUrl = process.env.SUPABASE_URL;
        const supabaseKey = process.env.SUPABASE_KEY;

        if (!supabaseUrl || !supabaseKey) {
            throw new Error("Supabase URL or Key is not defined in environment variables.");
        }

        this.client = createClient(supabaseUrl, supabaseKey);
    }

    async getConcerts(): Promise<Concert[]> {
        console.log('Database: Fetching concerts.');
        const pageSize = 1000;
        const all: Concert[] = [];
        let from = 0;

        while (true) {
            const to = from + pageSize - 1;
            const { data, error } = await this.client
                .from('concerts')
                .select('*')
                .range(from, to);

            if (error) {
                console.error('Error fetching concerts:', error);
                return all.length > 0 ? all : [];
            }

            const page = data || [];
            all.push(...page);

            if (page.length < pageSize) {
                break;
            }
            from += pageSize;
        }

        console.log(`Database: Found ${all.length} concerts.`);
        return all;
    }

    async saveConcerts(concerts: Concert[]): Promise<void> {
        console.log(`Database: Saving ${concerts.length} new concerts.`);
        const records = concerts.map(c => ({
            id: c.id,
            venue: (c.venue || '').trim(),
            location: c.location,
            date: c.date,
            details: c.details,
        }));
        
        const { error } = await this.client
            .from('concerts')
            .upsert(records, { onConflict: 'id' });

        if (error) {
            console.error('Error saving concerts:', error);
            throw new Error(`Failed to save concerts: ${error.message}`);
        } else {
            console.log('Database: Successfully saved concerts.');
        }
    }

    async getConcertsByDate(date: string): Promise<Concert[]> {
        console.log(`Database: Fetching concerts for date: ${date}.`);
        const { data, error } = await this.client
            .from('concerts')
            .select('*')
            .eq('date', date);

        if (error) {
            console.error('Error fetching concerts by date:', error);
            return [];
        }

        console.log(`Database: Found ${data.length} concerts for date ${date}.`);
        return data as Concert[];
    }
}
