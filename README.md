# Discord Music Bot

Цей Discord-бот призначений для відтворення музики у голосових каналах.

## Інсталяція та налаштування

1. Склонуйте репозиторій:

    ```bash
    git clone https://github.com/your-username/discord-music-bot.git
    ```

2. Встановіть залежності:

    ```bash
    cd discord-music-bot
    pip install -r requirements.txt
    ```

3. Отримайте токен бота від Discord та збережіть його в файлі `token.py`:

    ```python
    TOKEN = 'your-bot-token-here'
    ```

## Використання

1. Запустіть бота:

    ```bash
    python bot.py
    ```

2. Підключіть бота до вашого сервера Discord.
   
3. Використовуйте команду `!play <url>` для відтворення музики з YouTube.

## Команди

- `!play <url>`: Відтворює аудіо з вказаного URL.
- `!pause`: Призупиняє відтворення аудіо.
- `!resume`: Продовжує відтворення аудіо після паузи.
- `!stop`: Зупиняє відтворення аудіо і відключає бота від голосового каналу.
- `!volume <level>`: Змінює гучність відтворення аудіо (від 0 до 100).

## Завдяки

Цей бот створений за допомогою Discord.py та yt_dlp.

## Ліцензія

Цей проект ліцензований під MIT License - подробиці в файлі [LICENSE](LICENSE).
