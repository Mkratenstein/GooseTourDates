import 'dotenv/config';
import { Bot } from './bot';

async function main() {
    console.log('Bot is starting...');
    const bot = new Bot();

    const shutdown = async (signal: string) => {
        console.log(`Received ${signal}. Shutting down...`);
        await bot.shutdown();
        process.exit(0);
    };

    process.on('SIGINT', () => shutdown('SIGINT'));
    process.on('SIGTERM', () => shutdown('SIGTERM'));

    try {
        await bot.initialize();
        bot.start();
    } catch (error) {
        console.error('Error during bot startup:', error);
        process.exit(1);
    }
}

main().catch(error => {
    console.error('Unhandled error in main function:', error);
    process.exit(1);
});

process.on('unhandledRejection', error => {
    console.error('Unhandled promise rejection:', error);
});

process.on('uncaughtException', error => {
    console.error('Uncaught exception:', error);
    process.exit(1);
}); 