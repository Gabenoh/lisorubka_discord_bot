import discord
from discord.ext import commands
from yt_dlp import YoutubeDL
import asyncio
from pytube import Playlist
from utils.token import Token
import logging

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

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
global global_vol
global_vol = 0.10
queue = asyncio.Queue()


async def connect_to_voice(ctx):
    voice_channel = ctx.author.voice.channel
    if not voice_channel:
        logger.warning(
            f"Користувач {ctx.author.name} спробував підключитись до бота без підключення до голосового каналу на сервері {ctx.guild.name}.")
        await ctx.send("Ви повинні бути підключені до голосового каналу!")
        return

    if ctx.voice_client is None:
        await voice_channel.connect()
        logger.info(f"Бот підключився до голосового каналу '{voice_channel.name}' на сервері '{ctx.guild.name}'.")
    elif ctx.voice_client.channel != voice_channel:
        old_channel = ctx.voice_client.channel
        await ctx.voice_client.move_to(voice_channel)
        logger.info(
            f"Бот переміщено з голосового каналу '{old_channel.name}' до '{voice_channel.name}' на сервері '{ctx.guild.name}'.")
    return ctx.voice_client


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
        ydl_opts = {'noplaylist': True, 'quiet': True}
        with YoutubeDL(ydl_opts) as ydl:
            if 'https:' in url:
                info = ydl.extract_info(url, download=False)
                title = info['channel'] + ' - ' + info['title']
                stream = info['requested_formats'][1]['url']
            else:
                info = ydl.extract_info(f"ytsearch:{url}", download=False)
                stream = info['entries'][0]['requested_formats'][1]['url']
                title = info['entries'][0]['title']
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
    if not queue.empty():
        await clear_messages(ctx)
        track_url_title = await queue.get()
        logger.info(f"Початок відтворення треку '{track_url_title[1]}' на сервері '{ctx.guild.name}'.")
        await ctx.send(f'Зараз грає : {track_url_title[1]}')
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(track_url_title[0], **FFMPEG_OPTIONS),
                                              volume=global_vol)
        voice_client.play(source, after=lambda e: bot.loop.create_task(play_next(ctx)))
    else:
        logger.info(
            f"Черга відтворення закінчилась на сервері {ctx.guild.name}. Бот відключається від голосового каналу.")
        await ctx.send('У черзі закінчились треки')
        await voice_client.disconnect()


@bot.command(name="play", aliases=['p', 'п', 'П', 'P'])
async def play(ctx, *, url):
    await clear_messages(ctx)
    await play_music(ctx, url)


@bot.tree.command(name="play", description="Відтворити музику за URL")
async def slash_play(interaction: discord.Interaction, url: str):
    # Respond immediately to the interaction
    await interaction.response.send_message(f"Додаю до черги: {url}")
    logger.info(
        f"Користувач {interaction.user.name} запустив відтворення '{url}' через слеш-команду на сервері '{interaction.guild.name}'.")

    # Get context and process the command
    ctx = await bot.get_context(interaction)

    # Process the music - this can take time, but we've already responded to the interaction
    await play_music(ctx, url)


@bot.tree.command(name="search", description="Знайти музику в ютуб")
async def slash_search(interaction: discord.Interaction, name: str):
    # Respond immediately to the interaction
    await interaction.response.send_message(f"Шукаю та додаю до черги: {name}")
    logger.info(
        f"Користувач {interaction.user.name} запустив пошук '{name}' через слеш-команду на сервері '{interaction.guild.name}'.")

    # Get context and process the command
    ctx = await bot.get_context(interaction)

    # Process the search - this can take time, but we've already responded to the interaction
    await play_music(ctx, name)


@bot.command(name="next", aliases=['n', 'н', 'наступний'])
async def next_track(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        logger.info(f"Користувач {ctx.author.name} пропустив трек на сервері '{ctx.guild.name}'.")
        await clear_messages(ctx, 1)
    else:
        await ctx.send("Зараз нічого не грає.")


@bot.command(name="clearqueue", aliases=['к', 'черга'])
async def clean_queue(ctx):
    global queue
    if not queue.empty():
        queue = asyncio.Queue()
        await ctx.send("Черга очищена.")
        logger.info(f"Чергу очищено користувачем {ctx.author.name} на сервері '{ctx.guild.name}'.")
    else:
        await ctx.send("Черга і так порожня.")


@bot.command(name="clean_queue", description="Очищення черги відтворення")
async def slash_clean_queue(interaction: discord.Interaction):
    ctx = await bot.get_context(interaction)
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
            voice_client.source.volume = volume
            global_vol = volume
            await ctx.send(f"Гучність бота була встановлена на {volume * 100}%")
            logger.info(
                f"Гучність бота встановлено на {volume * 100}% користувачем {ctx.author.name} на сервері '{ctx.guild.name}'.")
        else:
            await ctx.send("Будь ласка, вкажіть значення гучності від 0 до 100.")
    else:
        await ctx.send("Бот не підключений до голосового каналу.")


@bot.tree.command(name="volume", description="Встановити гучність відтворення (0-100)")
async def slash_volume(interaction: discord.Interaction, volume: int = 10):
    ctx = await bot.get_context(interaction)

    global global_vol
    voice_client = ctx.voice_client
    if voice_client:
        if 0 <= volume <= 100:
            volume = volume / 100
            voice_client.source.volume = volume
            global_vol = volume
            await interaction.response.send_message(f"Гучність бота встановлена на {volume * 100}%")
            logger.info(
                f"Гучність бота встановлено на {volume * 100}% користувачем {interaction.user.name} на сервері '{interaction.guild.name}'.")
        else:
            await interaction.response.send_message("Будь ласка, вкажіть значення гучності від 0 до 100.")
    else:
        await interaction.response.send_message("Бот не підключений до голосового каналу.")


@bot.tree.command(name="stop", description="Зупинити відтворення та очистити чергу")
async def slash_stop(interaction: discord.Interaction):
    ctx = await bot.get_context(interaction)

    voice_client = ctx.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        global queue
        queue = asyncio.Queue()
        await voice_client.disconnect()
        logger.info(
            f"Відтворення зупинено та бот відключився від голосового каналу на сервері '{ctx.guild.name}' за запитом користувача {interaction.user.name}.")
        await interaction.response.send_message("Відтворення зупинено, черга очищена.")
    else:
        await interaction.response.send_message("Бот не підключений до голосового каналу або нічого не відтворює.")


@bot.tree.command(name="next", description="Перейти до наступного треку")
async def slash_next(interaction: discord.Interaction):
    ctx = await bot.get_context(interaction)

    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        logger.info(f"Користувач {interaction.user.name} пропустив трек на сервері '{ctx.guild.name}'.")
        await interaction.response.send_message("Перехід до наступного треку...")
    else:
        await interaction.response.send_message("Зараз нічого не грає.")


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
        'force_generic_extractor': True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(playlist_url, download=False)
            logger.debug(f"Інформація про плейлист '{playlist_url}': {info_dict}")
            if 'entries' in info_dict:
                playlist_entries = info_dict['entries']
                if len(playlist_entries) > 0:
                    await ctx.send(
                        f"Плейлист {info_dict['title']} містить {len(playlist_entries[:25])} треків. Додаємо до черги...")
                    for entry in playlist_entries[:25]:
                        if 'url' in entry:
                            await play_music(ctx, entry['url'])
                            await asyncio.sleep(1)
                    await ctx.send(
                        f"Плейлист {info_dict['title']} з перших {len(playlist_entries[:25])} треків доданий до черги.")

                    if not ctx.voice_client.is_playing():
                        await play_next(ctx)
                else:
                    await ctx.send(f"Плейлист порожній або не вдалося знайти треки.")
            elif info_dict.get('_type') == 'playlist':
                playlist = Playlist(playlist_url)
                playlist_url_list = list(playlist.video_urls)
                if len(playlist_url_list) >= 1:
                    await ctx.send(f"Плейлист налічує {len(playlist_url_list[:25])} треків. Додаємо до черги...")
                    for url in playlist_url_list[:25]:
                        await play_music(ctx, url)
                        await asyncio.sleep(1)
                    await ctx.send(f"Перші {len(playlist_url_list[:25])} треків з плейлиста додано до черги.")
                    if not ctx.voice_client.is_playing():
                        await play_next(ctx)
                else:
                    await ctx.send("Плейлист порожній або не містить дійсних посилань на відео.")
            else:
                await ctx.send("Не вдалося знайти треки в плейлисті.")
    except Exception as e:
        logger.error(f"Помилка при обробці плейлиста '{playlist_url}' на сервері {ctx.guild.name}: {e}")
        await ctx.send(f"Помилка при додаванні плейлисту: {e}")


@bot.tree.command(name="playlist", description="Додати плейлист до черги")
async def slash_playlist(interaction: discord.Interaction, playlist_url: str):
    # Immediately respond to the interaction
    await interaction.response.send_message(f"Обробка плейлиста: {playlist_url}")

    ctx = await bot.get_context(interaction)

    # Create a channel for further updates
    channel = interaction.channel

    voice_client = await connect_to_voice(ctx)
    if not voice_client:
        await channel.send("Не вдалося підключитися до голосового каналу.")
        return

    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'skip_download': True,
        'force_generic_extractor': True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(playlist_url, download=False)
            logger.debug(f"Інформація про плейлист '{playlist_url}': {info_dict}")
            if 'entries' in info_dict:
                playlist_entries = info_dict['entries']
                if len(playlist_entries) > 0:
                    await channel.send(
                        f"Плейлист {info_dict['title']} містить {len(playlist_entries[:25])} треків. Додаємо до черги...")
                    for entry in playlist_entries[:25]:
                        if 'url' in entry:
                            await play_music(ctx, entry['url'])
                            await asyncio.sleep(1)
                    await channel.send(
                        f"Плейлист {info_dict['title']} з перших {len(playlist_entries[:25])} треків доданий до черги.")

                    if not ctx.voice_client.is_playing():
                        await play_next(ctx)
                else:
                    await channel.send(f"Плейлист порожній або не вдалося знайти треки.")
            elif info_dict.get('_type') == 'playlist':
                playlist = Playlist(playlist_url)
                playlist_url_list = list(playlist.video_urls)
                if len(playlist_url_list) >= 1:
                    await channel.send(f"Плейлист налічує {len(playlist_url_list[:25])} треків. Додаємо до черги...")
                    for url in playlist_url_list[:25]:
                        await play_music(ctx, url)
                        await asyncio.sleep(1)
                    await channel.send(f"Перші {len(playlist_url_list[:25])} треків з плейлиста додано до черги.")
                    if not ctx.voice_client.is_playing():
                        await play_next(ctx)
                else:
                    await channel.send("Плейлист порожній або не містить дійсних посилань на відео.")
            else:
                await channel.send("Не вдалося знайти треки в плейлисті.")
    except Exception as e:
        logger.error(f"Помилка при обробці плейлиста '{playlist_url}' на сервері {ctx.guild.name}: {e}")
        await channel.send(f"Помилка при додаванні плейлисту: {e}")

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


if __name__ == '__main__':
    bot.run(TOKEN)