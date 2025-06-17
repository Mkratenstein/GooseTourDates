// @ts-nocheck
import { Client, GatewayIntentBits, TextChannel, Interaction, MessageFlags, GuildMember } from 'discord.js';
import express from 'express';
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
            this.startHttpServer();
        });

        this.client.on('interactionCreate', async (interaction) => {
            if (!interaction.isCommand()) return;
            console.log(`Received interaction: ${interaction.commandName} (${interaction.id})`);
            try {
                await this.handleCommand(interaction);
            } catch (error: any) {
                console.error(`Error handling interaction ${interaction.id}:`, error);
                
                // If the interaction is unknown, it has expired. No use trying to reply.
                if (error.code === 10062) { // DiscordAPIError.Codes.UnknownInteraction
                    console.error('Interaction likely expired. Cannot send error reply.');
                    return;
                }

                if (interaction.isRepliable()) {
                    const message = { content: 'An error occurred while processing your command.', flags: [MessageFlags.Ephemeral] };
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
        cron.schedule('0 */4 * * *', () => this.checkTours('scheduled'));
        console.log('Scheduled tour check to run every 4 hours.');
    }

    private async checkTours(source: 'manual' | 'scheduled', channelId?: string): Promise<void> {
        console.log(`checkTours: Starting tour check from ${source} source.`);
        let statusMessage = '';
        try {
            const scrapedConcerts = await this.scraper.scrapeTourDates();
            const savedConcerts = await this.database.getConcerts();

            const newConcerts = scrapedConcerts.filter(sc => {
                const scrapedDate = new Date(sc.date);
                return !savedConcerts.some(saved => {
                    const savedDate = new Date(saved.date);
                    return saved.venue === sc.venue &&
                           savedDate.getUTCFullYear() === scrapedDate.getUTCFullYear() &&
                           savedDate.getUTCMonth() === scrapedDate.getUTCMonth() &&
                           savedDate.getUTCDate() === scrapedDate.getUTCDate();
                });
            });

            // Sort new concerts by date in ascending order before processing
            newConcerts.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

            if (newConcerts.length > 0) {
                console.log(`checkTours: Found ${newConcerts.length} new concerts.`);
                await this.database.saveConcerts(newConcerts);
                await this.postConcerts(newConcerts);
                statusMessage = `Scrape complete. Found and posted ${newConcerts.length} new concerts.`;
            } else {
                console.log('checkTours: No new concerts found.');
                statusMessage = 'Scrape complete. No new concerts found.';
            }
        } catch (error) {
            console.error('Error checking tours:', error);
            statusMessage = 'An error occurred while checking for tours. Please check the logs.';
        } finally {
            console.log('checkTours: Finished tour check.');
            if (source === 'manual' && channelId) {
                try {
                    const channel = await this.client.channels.fetch(channelId);
                    if (channel?.isTextBased()) {
                        await channel.send(statusMessage);
                    }
                } catch (e) {
                    console.error(`Failed to send status update to channel ${channelId}:`, e);
                }
            }
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
            // Re-format the date to be more readable, e.g., "September 17, 2025"
            const date = new Date(`${concert.date}T12:00:00Z`); // Use noon UTC to avoid timezone issues
            const formattedDate = date.toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric',
                timeZone: 'UTC' 
            });

            const messageParts = [
                'Goose the Organization has announced a new show!',
                '',
                formattedDate,
                `${concert.venue} | ${concert.location}`
            ];

            if (concert.details) {
                messageParts.push(concert.details);
            }

            messageParts.push('');
            messageParts.push(`🎫 tickets: https://link.seated.com/${concert.id}`);

            const message = messageParts.join('\n');

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
            {
                name: 'postbydate',
                description: 'Post concerts from the database for a specific date (Admin only).',
                options: [
                    {
                        name: 'date',
                        type: 3, // String
                        description: 'The date of the concerts to post (YYYY-MM-DD).',
                        required: true,
                    },
                ],
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
            await interaction.reply({ content: '✅ Scrape job received. I will post the results here shortly.', flags: [MessageFlags.Ephemeral] });
            
            fetch(`http://localhost:${process.env.PORT || 8080}/scrape-job`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ channelId: interaction.channelId }),
            }).catch(e => console.error('Failed to dispatch scrape job to internal server:', e));

        } else if (commandName === 'status') {
            await interaction.reply({ content: 'Bot is running and operational.', flags: [MessageFlags.Ephemeral] });
        } else if (commandName === 'postbydate') {
            const adminRoleId = '680100291806363673';
            const member = interaction.member as GuildMember;

            if (!member.roles.cache.has(adminRoleId)) {
                return interaction.reply({ content: 'You do not have permission to use this command.', flags: [MessageFlags.Ephemeral] });
            }

            const date = interaction.options.getString('date', true);
            
            if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
                return interaction.reply({ content: 'Please provide the date in YYYY-MM-DD format.', flags: [MessageFlags.Ephemeral] });
            }

            await interaction.reply({ content: `Searching for concerts on ${date}...`, flags: [MessageFlags.Ephemeral] });

            try {
                const concertsToPost = await this.database.getConcertsByDate(date);

                if (concertsToPost.length > 0) {
                    await this.postConcerts(concertsToPost);
                    await interaction.followUp({ content: `Found and posted ${concertsToPost.length} concerts for ${date}.`, flags: [MessageFlags.Ephemeral] });
                } else {
                    await interaction.followUp({ content: `No concerts found in the database for ${date}.`, flags: [MessageFlags.Ephemeral] });
                }
            } catch (error) {
                console.error(`Error handling postbydate command for date ${date}:`, error);
                await interaction.followUp({ content: 'An error occurred while fetching concerts from the database.', flags: [MessageFlags.Ephemeral] });
            }
        }
        console.log(`handleCommand: Finished processing command '${commandName}'.`);
    }

    private startHttpServer(): void {
        const app = express();
        const port = process.env.PORT || 8080;

        app.use(express.json());

        app.post('/scrape-job', (req, res) => {
            const { channelId } = req.body;
            if (!channelId) {
                console.error('HTTP /scrape-job received without a channelId.');
                return res.status(400).send({ error: 'channelId is required' });
            }
            
            console.log(`HTTP /scrape-job received for channel ${channelId}. Kicking off background scrape.`);
            res.status(202).send({ message: 'Scrape job accepted.' });

            this.checkTours('manual', channelId).catch(error => {
                console.error('Error during background scrape initiated via HTTP:', error);
            });
        });

        app.get('/health', (req, res) => {
            res.status(200).send({ status: 'ok' });
        });

        app.listen(port, () => {
            console.log(`Internal HTTP server listening on port ${port}`);
        });
    }
} 