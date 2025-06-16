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
        const { data, error } = await this.client
            .from('concerts')
            .select('venue, date, location');

        if (error) {
            console.error('Error fetching concerts:', error);
            return [];
        }

        console.log(`Database: Found ${data.length} concerts.`);
        return data;
    }

    async saveConcerts(concerts: Concert[]): Promise<void> {
        console.log(`Database: Saving ${concerts.length} new concerts.`);
        const records = concerts.map(c => ({
            venue: c.venue,
            location: c.location,
            date: c.date,
        }));
        
        const { error } = await this.client
            .from('concerts')
            .insert(records);

        if (error) {
            console.error('Error saving concerts:', error);
        } else {
            console.log('Database: Successfully saved concerts.');
        }
    }
} 