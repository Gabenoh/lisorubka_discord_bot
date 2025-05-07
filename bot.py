import discord
from discord.ext import commands
from yt_dlp import YoutubeDL
import asyncio
from pytube import Playlist
from utils.token import Token
import logging
import random
import time
import re

# Налаштування базового логування
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                    filename='/home/galmed/discord_bot/logs/bot.log')
logger = logging.getLogger(__name__)


class MyBot(commands.Bot):
    async def on_ready(self):
        await self.tree.sync()
        logger.info(f"Logged in as {self.user}")


TOKEN = Token
intents = discord.Intents.all()
intents.members = True

bot = MyBot(command_prefix='!', intents=intents)

global global_vol
global_vol = 0.10
queue = asyncio.Queue()

# Розширений список User-Agent для більшої різноманітності
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/108.0.0.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
]

# Різноманітні заголовки Accept для більшої різноманітності
ACCEPT_HEADERS = [
    'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
]

# Різні мови для заголовка Accept-Language
ACCEPT_LANGUAGES = [
    'uk,en-US;q=0.7,en;q=0.3',
    'en-US,en;q=0.9',
    'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
    'en-GB,en;q=0.9,en-US;q=0.8',
    'de,en-US;q=0.7,en;q=0.3'
]

# Спрощені FFMPEG опції для кращої сумісності
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -bufsize 4096k'
}


# Функція для створення випадкових заголовків HTTP
def get_random_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': random.choice(ACCEPT_HEADERS),
        'Accept-Language': random.choice(ACCEPT_LANGUAGES),
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Sec-CH-UA': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        'Sec-CH-UA-Mobile': '?0',
        'Sec-CH-UA-Platform': '"Windows"',
        'Origin': 'https://www.youtube.com',
        'Referer': 'https://www.youtube.com/'
    }


async def play_music(ctx, url):
    try:
        voice_client = await connect_to_voice(ctx)
        if not voice_client:
            return
    except Exception as e:
        logger.error(f"Помилка під час підключення до голосового каналу на сервері {ctx.guild.name}: {e}")
        return

    voice_client = ctx.voice_client
    try:
        # Оновлені налаштування yt-dlp для обходу обмежень
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            # Важливі опції для обходу обмежень
            'extractor_retries': 10,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'socket_timeout': 30,
            'retries': 10,
            'fragment_retries': 10,
            # Додамо cookie файл, якщо він є
            # 'cookiefile': '/path/to/cookies.txt',  # Розкоментуйте і вкажіть шлях до файлу з cookies, якщо маєте
            # Випадковий User-Agent та інші заголовки для імітації реального користувача
            'http_headers': get_random_headers()
        }

        # Додаємо невелику затримку, щоб запити не виглядали автоматизованими
        await asyncio.sleep(random.uniform(0.5, 2.0))

        with YoutubeDL(ydl_opts) as ydl:
            if 'https:' in url:
                # Спроба отримати інформацію, повторюємо кілька разів у випадку невдачі
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        # Оновлюємо заголовки для кожної спроби
                        ydl_opts['http_headers'] = get_random_headers()
                        ydl = YoutubeDL(ydl_opts)

                        info = ydl.extract_info(url, download=False)

                        if info.get('channel') and info.get('title'):
                            title = f"{info['channel']} - {info['title']}"
                        else:
                            title = info.get('title', 'Невідомий трек')

                        # Отримання найкращого аудіо URL
                        if 'formats' in info:
                            # Спочатку шукаємо чисто аудіо формати з високою якістю
                            audio_formats = [f for f in info['formats']
                                             if f.get('acodec') != 'none' and
                                             (f.get('vcodec') == 'none' or f.get('vcodec') is None or f.get(
                                                 'vcodec') == 'n/a')]

                            if audio_formats:
                                # Сортуємо за якістю звуку (abr — audio bitrate)
                                audio_formats.sort(key=lambda x: (
                                    x.get('abr', 0) if x.get('abr') else 0,
                                    x.get('asr', 0) if x.get('asr') else 0  # audio sample rate
                                ), reverse=True)

                                # Віддаємо перевагу opus форматам, які зазвичай працюють краще з ffmpeg
                                opus_formats = [f for f in audio_formats if f.get('acodec') == 'opus']
                                if opus_formats:
                                    stream = opus_formats[0]['url']
                                else:
                                    stream = audio_formats[0]['url']
                            else:
                                # Якщо немає чисто аудіо форматів, використовуємо URL за замовчуванням
                                stream = info.get('url', info.get('webpage_url'))
                        else:
                            # Резервний варіант, якщо не знайдено форматів
                            stream = info.get('url', info.get('webpage_url'))

                        # Успішно отримали потік, виходимо з циклу спроб
                        break
                    except Exception as e:
                        logger.warning(f"Спроба {attempt + 1}/{max_retries} отримати інформацію не вдалася: {e}")
                        if attempt == max_retries - 1:  # Остання спроба не вдалася
                            raise
                        # Змінюємо інтервал очікування між спробами
                        await asyncio.sleep(random.uniform(1.5, 4.0))
            else:
                # Пошук на YouTube
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        # Оновлюємо заголовки для кожної спроби
                        ydl_opts['http_headers'] = get_random_headers()
                        ydl = YoutubeDL(ydl_opts)

                        # Видаляємо спеціальні символи для пошуку
                        search_term = re.sub(r'[^\w\s]', '', url)
                        info = ydl.extract_info(f"ytsearch:{search_term}", download=False)

                        if 'entries' in info and info['entries']:
                            entry = info['entries'][0]
                            title = entry.get('title', 'Невідомий трек')

                            # Так само шукаємо найкращий аудіо формат
                            if 'formats' in entry:
                                audio_formats = [f for f in entry['formats']
                                                 if f.get('acodec') != 'none' and
                                                 (f.get('vcodec') == 'none' or f.get('vcodec') is None or f.get(
                                                     'vcodec') == 'n/a')]

                                if audio_formats:
                                    # Сортуємо за якістю звуку
                                    audio_formats.sort(key=lambda x: (
                                        x.get('abr', 0) if x.get('abr') else 0,
                                        x.get('asr', 0) if x.get('asr') else 0
                                    ), reverse=True)

                                    # Віддаємо перевагу певним форматам
                                    preferred_formats = [f for f in audio_formats
                                                         if f.get('ext') in ['m4a', 'opus', 'webm', 'mp4']]

                                    if preferred_formats:
                                        stream = preferred_formats[0]['url']
                                    else:
                                        stream = audio_formats[0]['url']
                                else:
                                    stream = entry.get('url', entry.get('webpage_url'))
                            else:
                                stream = entry.get('url', entry.get('webpage_url'))
                        else:
                            raise Exception("Не вдалося знайти відео")

                        # Успішно отримали потік, виходимо з циклу спроб
                        break
                    except Exception as e:
                        logger.warning(f"Спроба {attempt + 1}/{max_retries} пошуку не вдалася: {e}")
                        if attempt == max_retries - 1:  # Остання спроба не вдалася
                            raise
                        # Змінюємо інтервал очікування між спробами
                        await asyncio.sleep(random.uniform(1.5, 4.0))

            # Додаємо унікальний параметр до URL для запобігання кешуванню
            timestamp = int(time.time())
            stream = f"{stream}{'&' if '?' in stream else '?'}nocache={timestamp}"

            await queue.put([stream, title])
            logger.info(f"До черги додано трек '{title}' ({url}) на сервері '{ctx.guild.name}'.")
            if not voice_client.is_playing():
                await play_next(ctx)
    except Exception as e:
        logger.error(f"Помилка під час відтворення музики за посиланням '{url}' на сервері {ctx.guild.name}: {e}")
        await ctx.send(f"Помилка під час відтворення музики: {e}")


async def play_next(ctx):
    global global_vol
    voice_client = ctx.voice_client
    if not voice_client:
        return

    if not queue.empty():
        await clear_messages(ctx)
        track_url_title = await queue.get()
        logger.info(f"Початок відтворення треку '{track_url_title[1]}' на сервері '{ctx.guild.name}'.")
        await ctx.send(f'Зараз грає : {track_url_title[1]}')

        try:
            # Намагаємося відтворити трек з кількома спробами, якщо потрібно
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    source = discord.PCMVolumeTransformer(
                        discord.FFmpegPCMAudio(track_url_title[0], **FFMPEG_OPTIONS),
                        volume=global_vol
                    )

                    voice_client.play(
                        source,
                        after=lambda e: asyncio.run_coroutine_threadsafe(
                            handle_playback_error(ctx, e),
                            bot.loop
                        )
                    )
                    # Успішно почали відтворення
                    break
                except Exception as e:
                    logger.warning(f"Спроба {attempt + 1}/{max_retries} відтворити трек не вдалася: {e}")
                    if attempt == max_retries - 1:  # Остання спроба не вдалася
                        raise
                    # Невелика затримка перед наступною спробою
                    await asyncio.sleep(random.uniform(1.0, 2.0))

        except Exception as e:
            logger.error(f"Помилка при відтворенні треку: {e}")
            await ctx.send(f"Помилка при відтворенні треку: {e}")
            # Спробуємо перейти до наступного треку
            await asyncio.sleep(1)
            await play_next(ctx)
    else:
        logger.info(
            f"Черга відтворення закінчилась на сервері {ctx.guild.name}. Бот відключається від голосового каналу.")
        await ctx.send('У черзі закінчились треки')
        await voice_client.disconnect()


# Функція для обробки помилок
async def handle_playback_error(ctx, error):
    if error:
        logger.error(f"Помилка при відтворенні: {error}")
        await ctx.send(f"Помилка при відтворенні. Переходжу до наступного треку.")
    await play_next(ctx)


async def connect_to_voice(ctx):
    try:
        voice_channel = ctx.author.voice.channel
        if not voice_channel:
            logger.warning(
                f"Користувач {ctx.author.name} спробував підключитись до бота без підключення до голосового каналу на сервері {ctx.guild.name}.")
            await ctx.send("Ви повинні бути підключені до голосового каналу!")
            return None
    except AttributeError:
        await ctx.send("Ви повинні бути підключені до голосового каналу!")
        return None

    try:
        if ctx.voice_client is None:
            await voice_channel.connect()
            logger.info(f"Бот підключився до голосового каналу '{voice_channel.name}' на сервері '{ctx.guild.name}'.")
        elif ctx.voice_client.channel != voice_channel:
            old_channel = ctx.voice_client.channel
            await ctx.voice_client.move_to(voice_channel)
            logger.info(
                f"Бот переміщено з голосового каналу '{old_channel.name}' до '{voice_channel.name}' на сервері '{ctx.guild.name}'.")
        return ctx.voice_client
    except Exception as e:
        logger.error(f"Помилка при підключенні до голосового каналу: {e}")
        await ctx.send(f"Не вдалося підключитися до голосового каналу: {e}")
        return None


@bot.command(name="play", aliases=['p', 'п', 'П', 'P'])
async def play(ctx, *, url):
    await clear_messages(ctx)
    await play_music(ctx, url)


@bot.tree.command(name="play", description="Відтворити музику за URL")
async def slash_play(interaction: discord.Interaction, url: str):
    ctx = await bot.get_context(interaction)
    await clear_messages(ctx)
    await play_music(ctx, url)
    await interaction.response.send_message(f"Відтворюю: {url}")
    logger.info(
        f"Користувач {interaction.user.name} запустив відтворення '{url}' через слеш-команду на сервері '{interaction.guild.name}'.")


@bot.command(name="next", aliases=['n', 'н', 'наступний'])
async def next_track(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        logger.info(f"Користувач {ctx.author.name} пропустив трек на сервері '{ctx.guild.name}'.")
        await clear_messages(ctx, 1)
    else:
        await ctx.send("Зараз нічого не грає.")


@bot.command(name="k", aliases=['к', 'черга'])
async def clean_queue(ctx):
    global queue
    if not queue.empty():
        queue = asyncio.Queue()
        await ctx.send("Черга очищена.")
        logger.info(f"Чергу очищено користувачем {ctx.author.name} на сервері '{ctx.guild.name}'.")
    else:
        await ctx.send("Черга і так порожня.")


@bot.command(name="stop", aliases=['стоп', 'с', 's'])
async def stop(ctx):
    voice_client = ctx.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await clean_queue(ctx)
        await voice_client.disconnect()
        logger.info(
            f"Відтворення зупинено та бот відключився від голосового каналу на сервері '{ctx.guild.name}' за запитом користувача {ctx.author.name}.")
        await clear_messages(ctx, 1)
    else:
        await ctx.send("Бот не підключений до голосового каналу або нічого не відтворює.")


@bot.command(name='pause', aliases=['пауза'], help='This command pauses the song')
async def pause(ctx):
    voice_client = ctx.voice_client
    if voice_client is not None and voice_client.is_playing():
        voice_client.pause()
        logger.info(f"Відтворення призупинено користувачем {ctx.author.name} на сервері '{ctx.guild.name}'.")
    else:
        await ctx.send("На данний момент нічого не відтворюється")


@bot.command(name='resume', aliases=['старт', 'start'], help='Resumes the song')
async def resume(ctx):
    voice_client = ctx.voice_client
    if voice_client is not None and voice_client.is_paused():
        voice_client.resume()
        logger.info(f"Відтворення відновлено користувачем {ctx.author.name} на сервері '{ctx.guild.name}'.")
    else:
        await ctx.send("Бот нічого не відтворює. використай !play </url_for_music_video> команду")


@bot.command(name="volume", aliases=['vol', 'з'])
async def set_volume(ctx, volume: int = 10):
    global global_vol
    voice_client = ctx.voice_client
    if voice_client:
        if 0 <= volume <= 100:
            volume = volume / 100
            if hasattr(voice_client, 'source'):
                voice_client.source.volume = volume
            global_vol = volume
            await ctx.send(f"Гучність бота була встановлена на {volume * 100}%")
            logger.info(
                f"Гучність бота встановлено на {volume * 100}% користувачем {ctx.author.name} на сервері '{ctx.guild.name}'.")
        else:
            await ctx.send("Будь ласка, вкажіть значення гучності від 0 до 100.")
    else:
        await ctx.send("Бот не підключений до голосового каналу.")


@bot.command(name="playlist", aliases=['pl', 'пл', 'плейлист'])
async def playlist(ctx, playlist_url):
    await clear_messages(ctx)

    voice_client = await connect_to_voice(ctx)
    if not voice_client:
        return

    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'skip_download': True,
        'force_generic_extractor': False,
        'extractor_retries': 10,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'socket_timeout': 30,
        'retries': 10,
        'fragment_retries': 10,
        'http_headers': get_random_headers()
    }

    try:
        # Додаємо затримку, щоб запити не виглядали автоматизованими
        await asyncio.sleep(random.uniform(0.5, 2.0))

        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Оновлюємо заголовки для кожної спроби
                ydl_opts['http_headers'] = get_random_headers()
                ydl = YoutubeDL(ydl_opts)

                info_dict = ydl.extract_info(playlist_url, download=False)
                logger.debug(f"Інформація про плейлист '{playlist_url}': отримано")

                if 'entries' in info_dict and info_dict['entries']:
                    playlist_entries = info_dict['entries']
                    if len(playlist_entries) > 0:
                        playlist_title = info_dict.get('title', 'Плейлист')
                        await ctx.send(
                            f"Плейлист '{playlist_title}' містить {len(playlist_entries[:25])} треків. Додаємо до черги...")

                        for entry in playlist_entries[:25]:
                            if 'url' in entry or 'id' in entry:
                                video_url = entry.get('url', f"https://www.youtube.com/watch?v={entry['id']}")
                                # Затримка між додаванням треків для зменшення навантаження
                                await play_music(ctx, video_url)
                                await asyncio.sleep(random.uniform(0.8, 2.0))

                        await ctx.send(
                            f"Плейлист '{playlist_title}' з перших {len(playlist_entries[:25])} треків доданий до черги.")

                        if not ctx.voice_client.is_playing():
                            await play_next(ctx)

                        # Успішно обробили плейлист
                        break
                    else:
                        await ctx.send(f"Плейлист порожній або не вдалося знайти треки.")
                elif info_dict.get('_type') == 'playlist':
                    # Спробуємо використати pytube як запасний варіант
                    try:
                        # Додаткова затримка перед використанням іншої бібліотеки
                        await asyncio.sleep(random.uniform(1.0, 2.5))

                        playlist = Playlist(playlist_url)
                        playlist_url_list = list(playlist.video_urls)

                        if playlist_url_list:
                            await ctx.send(
                                f"Плейлист налічує {len(playlist_url_list[:25])} треків. Додаємо до черги...")

                            for url in playlist_url_list[:25]:
                                await play_music(ctx, url)
                                # Варіюємо затримку між треками
                                await asyncio.sleep(random.uniform(0.8, 2.0))

                            await ctx.send(f"Перші {len(playlist_url_list[:25])} треків з плейлиста додано до черги.")

                            if ctx.voice_client and not ctx.voice_client.is_playing():
                                await play_next(ctx)

                            # Успішно обробили плейлист через pytube
                            break
                        else:
                            await ctx.send("Плейлист порожній або не містить дійсних посилань на відео.")
                    except Exception as pytube_error:
                        logger.warning(f"Помилка при обробці плейлиста через pytube: {pytube_error}")
                        # Якщо це остання спроба, потрібно повідомити користувача
                        if attempt == max_retries - 1:
                            await ctx.send("Не вдалося знайти треки в плейлисті.")
                            raise
                else:
                    # Якщо це остання спроба і все ще не вдалося
                    if attempt == max_retries - 1:
                        await ctx.send("Не вдалося знайти треки в плейлисті.")
                        raise Exception("Неправильний формат плейлиста")

            except Exception as e:
                logger.warning(f"Спроба {attempt + 1}/{max_retries} обробити плейлист не вдалася: {e}")
                # Якщо це остання спроба, повідомляємо про помилку
                if attempt == max_retries - 1:
                    logger.error(f"Помилка при обробці плейлиста '{playlist_url}' на сервері {ctx.guild.name}: {e}")
                    await ctx.send(f"Помилка при додаванні плейлисту: {e}")
                    raise

                # Змінюємо інтервал очікування між спробами
                await asyncio.sleep(random.uniform(2.0, 5.0))
    except Exception as e:
        logger.error(f"Помилка при обробці плейлиста '{playlist_url}' на сервері {ctx.guild.name}: {e}")
        await ctx.send(f"Помилка при додаванні плейлисту: {e}")


@bot.command(name="clear", aliases=["clean", "delete", 'видали', 'очисти'])
async def clear_messages(ctx, amount: int = 0):
    try:
        deleted = await ctx.channel.purge(limit=amount + 1)
        if amount > 0:
            logger.info(
                f"Видалено {len(deleted)} повідомлень користувачем {ctx.author.name} в каналі`'{ctx.channel.name}' на сервері '{ctx.guild.name}'.")
    except discord.errors.NotFound:
        logger.warning(f"Спроба видалити повідомлення в неіснуючому каналі на сервері '{ctx.guild.name}'.")
    except discord.errors.Forbidden:
        logger.error(
            f"Бот не має дозволу на видалення повідомлень в каналі '{ctx.channel.name}' на сервері '{ctx.guild.name}'.")


# Додана команда для отримання інформації про версію yt-dlp
@bot.command(name="ytdlp_version", aliases=['ytv', 'version'])
async def ytdlp_version(ctx):
    try:
        import yt_dlp
        version = yt_dlp.version.__version__
        await ctx.send(f"Поточна версія yt-dlp: {version}")
        logger.info(f"Користувач {ctx.author.name} запитав версію yt-dlp: {version}")
    except Exception as e:
        await ctx.send(f"Помилка при отриманні версії yt-dlp: {e}")
        logger.error(f"Помилка при отриманні версії yt-dlp: {e}")


if __name__ == '__main__':
    bot.run(TOKEN)