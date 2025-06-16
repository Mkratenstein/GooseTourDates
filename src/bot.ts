import { Client, GatewayIntentBits, TextChannel, Interaction } from 'discord.js';
import { Scraper, Concert } from './scraper';
import { DatabaseService } from './database';
import cron from 'node-cron';

export class Bot {
    private client = new Client({
        intents: [
            GatewayIntentBits.Guilds,
            GatewayIntentBits.GuildMessages,
            GatewayIntentBits.MessageContent,
        ],
    });

    private scraper = new Scraper();
    private database = new DatabaseService();

    public start(): void {
        this.client.on('ready', () => {
            console.log(`Logged in as ${this.client.user?.tag}!`);
            this.scheduleTourCheck();
            this.registerCommands();
        });

        this.client.on('interactionCreate', (interaction) => {
            if (!interaction.isCommand()) return;
            this.handleCommand(interaction);
        });

        const token = process.env.DISCORD_TOKEN;
        if (!token) {
            throw new Error('DISCORD_TOKEN is not defined in the environment variables.');
        }
        
        this.client.login(token);
    }

    private scheduleTourCheck(): void {
        // Schedule to run every 4 hours
        cron.schedule('0 */4 * * *', () => this.checkTours());
        console.log('Scheduled tour check to run every 4 hours.');
    }

    private async checkTours(interaction?: Interaction): Promise<void> {
        try {
            if (interaction) {
                await (interaction as any).reply({ content: 'Checking for new tour dates...', ephemeral: true });
            } else {
                console.log('Checking for new tour dates...');
            }
            const scrapedConcerts = await this.scraper.scrapeTourDates();
            const savedConcerts = await this.database.getConcerts();

            const newConcerts = scrapedConcerts.filter(sc => !savedConcerts.includes(sc.venue));

            if (newConcerts.length > 0) {
                console.log(`Found ${newConcerts.length} new concerts!`);
                await this.database.saveConcerts(newConcerts);
                await this.postConcerts(newConcerts);
                if (interaction) {
                    await (interaction as any).followUp({ content: `Found and posted ${newConcerts.length} new concerts.`, ephemeral: true });
                }
            } else {
                console.log('No new concerts found.');
                if (interaction) {
                    await (interaction as any).followUp({ content: 'No new concerts found.', ephemeral: true });
                }
            }
        } catch (error) {
            console.error('Error checking tours:', error);
            if (interaction) {
                await (interaction as any).followUp({ content: 'An error occurred while checking for tours.', ephemeral: true });
            }
        } finally {
            await this.scraper.close();
        }
    }

    private async postConcerts(concerts: Concert[]): Promise<void> {
        const channelId = process.env.DISCORD_CHANNEL_ID;
        if (!channelId) {
            throw new Error('DISCORD_CHANNEL_ID is not defined in the environment variables.');
        }

        const channel = await this.client.channels.fetch(channelId);
        if (!channel || !(channel instanceof TextChannel)) {
            throw new Error(`Could not find channel with ID ${channelId}, or it is not a text channel.`);
        }

        for (const concert of concerts) {
            const message = `**New Goose Show Announced!**\n**Date:** ${concert.date}\n**Venue:** ${concert.venue}\n**Location:** ${concert.location}`;
            await channel.send(message);
        }
    }

    private async registerCommands(): Promise<void> {
        const commands = [
            {
                name: 'scrape',
                description: 'Manually trigger a search for new tour dates.',
            },
            {
                name: 'status',
                description: 'Check the status of the bot.',
            },
        ];

        try {
            await this.client.application?.commands.set(commands);
            console.log('Slash commands registered successfully.');
        } catch (error) {
            console.error('Failed to register slash commands:', error);
        }
    }

    private async handleCommand(interaction: Interaction): Promise<void> {
        if (!interaction.isCommand()) return;

        const { commandName } = interaction;

        if (commandName === 'scrape') {
            await this.checkTours(interaction);
        } else if (commandName === 'status') {
            await interaction.reply({ content: 'Bot is running and operational.', ephemeral: true });
        }
    }
} 