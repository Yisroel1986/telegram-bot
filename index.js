const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');

const app = express();
app.use(bodyParser.json());

const TELEGRAM_BOT_TOKEN = '<7808912428:AAEGkZgoStauhLqTar9O7IfSk-YsxXrEjpg>';
const TELEGRAM_API_URL = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}`;

async function sendMessage(chatId, text) {
    await axios.post(`${TELEGRAM_API_URL}/sendMessage`, {
        chat_id: chatId,
        text: text,
    });
}

app.post('/webhook', async (req, res) => {
    const body = req.body;

    if (body.message) {
        const chatId = body.message.chat.id;
        const text = body.message.text;

        if (text === '/start') {
            await sendMessage(chatId, 'Привет! Я помогу вам забронировать тур в зоопарк. Напишите, что вас интересует!');
        } else {
            await sendMessage(chatId, 'Извините, я пока вас не понял. Попробуйте написать что-то другое.');
        }
    }

    res.sendStatus(200);
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
