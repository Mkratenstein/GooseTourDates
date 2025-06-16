import 'dotenv/config';
import { Bot } from './bot';

console.log('Bot is starting...');

const bot = new Bot();

try {
    bot.start();
} catch (error) {
    console.error('Error during bot startup:', error);
    process.exit(1);
}

process.on('unhandledRejection', error => {
    console.error('Unhandled promise rejection:', error);
});

process.on('uncaughtException', error => {
    console.error('Uncaught exception:', error);
    process.exit(1);
}); 