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

    public async initialize(): Promise<void> {
        await this.scraper.initialize();
    }

    public start(): void {
        this.client.on('ready', () => {
            console.log(`Logged in as ${this.client.user?.tag}!`);
            this.scheduleTourCheck();
            this.registerCommands();
        });

        this.client.on('interactionCreate', async (interaction) => {
            if (!interaction.isCommand()) return;
            console.log(`Received interaction: ${interaction.commandName} (${interaction.id})`);
            try {
                await this.handleCommand(interaction);
            } catch (error) {
                console.error(`Error handling interaction ${interaction.id}:`, error);
                if (interaction.isRepliable()) {
                    const message = { content: 'An error occurred while processing your command.', ephemeral: true };
                    try {
                        if (interaction.replied || interaction.deferred) {
                            await interaction.followUp(message);
                        } else {
                            await interaction.reply(message);
                        }
                    } catch (e) {
                        console.error(`Failed to send error reply for interaction ${interaction.id}:`, e);
                    }
                }
            }
        });

        this.client.on('debug', (info) => console.log(`[DEBUG] ${info}`));
        this.client.on('warn', (info) => console.warn(`[WARN] ${info}`));
        this.client.on('error', (error) => console.error(`[ERROR] ${error.message}`));

        const token = process.env.DISCORD_TOKEN;
        if (!token) {
            throw new Error('DISCORD_TOKEN is not defined in the environment variables.');
        }
        
        this.client.login(token);
    }

    public async shutdown(): Promise<void> {
        console.log('Shutting down bot gracefully...');
        await this.scraper.close();
        this.client.destroy();
    }

    private scheduleTourCheck(): void {
        // Schedule to run every 4 hours
        cron.schedule('0 */4 * * *', () => this.checkTours());
        console.log('Scheduled tour check to run every 4 hours.');
    }

    private async checkTours(interaction?: Interaction): Promise<void> {
        console.log('checkTours: Starting tour check.');
        try {
            if (interaction) {
                // The initial reply is now handled by deferReply in the command handler
                console.log('Checking for new tour dates (triggered by interaction)...');
            } else {
                console.log('Checking for new tour dates (scheduled)...');
            }
            const scrapedConcerts = await this.scraper.scrapeTourDates();
            const savedConcerts = await this.database.getConcerts();

            const newConcerts = scrapedConcerts.filter(sc => !savedConcerts.some(saved => saved.venue === sc.venue && saved.date === sc.date));

            if (newConcerts.length > 0) {
                console.log(`checkTours: Found ${newConcerts.length} new concerts.`);
                await this.database.saveConcerts(newConcerts);
                await this.postConcerts(newConcerts);
                if (interaction) {
                    await (interaction as any).editReply({ content: `Found and posted ${newConcerts.length} new concerts.` });
                }
            } else {
                console.log('checkTours: No new concerts found.');
                if (interaction) {
                    await (interaction as any).editReply({ content: 'No new concerts found.' });
                }
            }
        } catch (error) {
            console.error('Error checking tours:', error);
            if (interaction?.isCommand()) {
                const message = { content: 'An error occurred while checking for tours.', ephemeral: true };
                if ((interaction as any).deferred || (interaction as any).replied) {
                    await (interaction as any).followUp(message);
                } else {
                    await (interaction as any).reply(message);
                }
            }
        } finally {
            console.log('checkTours: Finished tour check.');
        }
    }

    private async postConcerts(concerts: Concert[]): Promise<void> {
        console.log(`postConcerts: Attempting to post ${concerts.length} concerts.`);
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
            console.log(`postConcerts: Successfully posted announcement for ${concert.venue}.`);
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
            console.log('Registering slash commands...');
            await this.client.application?.commands.set(commands);
            console.log('Slash commands registered successfully.');
        } catch (error) {
            console.error('Failed to register slash commands:', error);
        }
    }

    private async handleCommand(interaction: Interaction): Promise<void> {
        if (!interaction.isCommand()) return;

        const { commandName } = interaction;
        console.log(`handleCommand: Processing command '${commandName}'.`);

        if (commandName === 'scrape') {
            await interaction.deferReply({ ephemeral: true });
            await this.checkTours(interaction);
        } else if (commandName === 'status') {
            await interaction.reply({ content: 'Bot is running and operational.', ephemeral: true });
        }
        console.log(`handleCommand: Finished processing command '${commandName}'.`);
    }
} 