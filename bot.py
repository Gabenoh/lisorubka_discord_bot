import discord
from discord.ext import commands
from yt_dlp import YoutubeDL
import asyncio
from pytube import Playlist
from utils.token import Token


class MyBot(commands.Bot):
    async def on_ready(self):
        # Синхронізація слеш-команд із Discord API
        await self.tree.sync()
        print(f"Logged in as {self.user}")


TOKEN = Token
intents = discord.Intents.all()
intents.members = True

# Замість стандартного створення бота, використовуємо новий клас
bot = MyBot(command_prefix='!', intents=intents)


# Створення змінної для зберігання URL-адреси
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
global global_vol
global_vol = 0.10
queue = asyncio.Queue()


async def connect_to_voice(ctx):
    """Функція для підключення до голосового каналу"""
    voice_channel = ctx.author.voice.channel
    if not voice_channel:
        await ctx.send("Ви повинні бути підключені до голосового каналу!")
        return

    # Перевіряємо, чи бот вже підключений до голосового каналу
    if ctx.voice_client is None:
        await voice_channel.connect()
    elif ctx.voice_client.channel != voice_channel:
        await ctx.voice_client.move_to(voice_channel)


async def play_music(ctx, url):
    try:
        await connect_to_voice(ctx)
    except Exception as e:
        print(e)

    voice_client = ctx.voice_client
    try:
        ydl_opts = {'noplaylist': True, 'quiet': True}
        with YoutubeDL(ydl_opts) as ydl:
            if 'https:' in url:
                info = ydl.extract_info(url, download=False)
                title = info['channel'] +' - ' + info['title']
                stream = info['requested_formats'][1]['url']
            else:
                info = ydl.extract_info(f"ytsearch:{url}", download=False)
                stream = info['entries'][0]['requested_formats'][1]['url']
                title = info['entries'][0]['title']
            # Додавання URL-адреси відео до черги
            await queue.put([stream, title])

            # Якщо бот не відтворює відео наразі, почніть відтворення
            if not voice_client.is_playing():
                await play_next(ctx)

    except Exception as e:
        await ctx.send(f"Помилка під час відтворення музики: {e}")


async def play_next(ctx):
    global global_vol
    voice_client = ctx.voice_client
    if not queue.empty():
        await clear_messages(ctx)
        track_url_title = await queue.get()
        await ctx.send(f'Зараз грає : {track_url_title[1]}')
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(track_url_title[0], **FFMPEG_OPTIONS),
                                              volume=global_vol)
        voice_client.play(source, after=lambda e: bot.loop.create_task(play_next(ctx)))
    else:
        await ctx.send('У черзі закінчились треки')
        await voice_client.disconnect()



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


@bot.command(name="next", aliases=['n', 'н', 'наступний'])
async def next_track(ctx):
    await clear_messages(ctx, 1)
    ctx.voice_client.stop()


@bot.command(name="k", aliases=['к', 'черга'])
async def clean_queue(ctx):
    global queue
    if not queue.empty():
        queue = asyncio.Queue()  # Очищаємо чергу, створивши нову порожню чергу
        await ctx.send("Черга очищена.")
    else:
        await ctx.send("Черга і так порожня.")


@bot.command(name="stop", aliases=['стоп', 'с', 's'])
async def stop(ctx):
    voice_client = ctx.voice_client
    await clear_messages(ctx, 1)
    if voice_client and voice_client.is_playing:
        voice_client.stop()
        await clean_queue(ctx)
        await voice_client.disconnect()


@bot.command(name='pause', aliases=['пауза'], help='This command pauses the song')
async def pause(ctx):
    voice_client = ctx.voice_client
    if voice_client is not None and voice_client.is_playing():
        voice_client.pause()
    else:
        await ctx.send("На данний момент нічого не відтворюється")


@bot.command(name='resume', aliases=['старт', 'start'], help='Resumes the song')
async def resume(ctx):
    voice_client = ctx.voice_client
    if voice_client is not None and voice_client.is_paused():
        voice_client.resume()
    else:
        await ctx.send("Бот нічого не відтворює. використай !play </url_for_music_video> команду")


@bot.command(name="volume", aliases=['vol', 'з'])
async def set_volume(ctx, volume: int = 10):
    global global_vol
    voice_client = ctx.voice_client
    if voice_client:
        # Перевіряємо, чи вказане значення гучності знаходиться в межах від 0 до 100
        if 0 <= volume <= 100:
            # Перетворюємо значення гучності у діапазон від 0 до 1 (де 1 - максимальна гучність)
            volume = volume / 100
            # Встановлюємо гучність для голосового каналу
            voice_client.source.volume = volume
            global_vol = volume
            await ctx.send(f"Гучність бота була встановлена на {volume * 100}%")
        else:
            await ctx.send("Будь ласка, вкажіть значення гучності від 0 до 100.")
    else:
        await ctx.send("Бот не підключений до голосового каналу.")


@bot.command(name="playlist", aliases=['pl', 'пл', 'плейлист'])
async def playlist(ctx, playlist_url):
    await clear_messages(ctx)

    # Перевіряємо, чи бот вже підключений до голосового каналу
    if ctx.voice_client is None:
        try:
            await connect_to_voice(ctx)  # Якщо не підключений, підключаємо
        except Exception as e:
            await ctx.send(f"Помилка підключення до голосового каналу: {e}")
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
            print(f'{info_dict=}')
            if 'entries' in info_dict:
                # Перевіряємо, чи є в плейлисті треки
                playlist_entries = info_dict['entries']
                if len(playlist_entries) > 0:
                    await ctx.send(
                        f"Плейлист {info_dict['title']} містить {len(playlist_entries[:25])} треків. Додаємо до черги...")
                    for entry in playlist_entries[:25]:  # Обмежуємо до 25 треків для запобігання перевантаження
                        if 'url' in entry:
                            await play_music(ctx, entry['url'])
                            await asyncio.sleep(1)
                    await ctx.send(
                        f"Плейлист {info_dict['title']} з перших {len(playlist_entries[:25])} треків доданий до черги.")

                    # Починаємо відтворення наступної пісні, якщо музика не грає
                    if not ctx.voice_client.is_playing():
                        await play_next(ctx)
                else:
                    await ctx.send(f"Плейлист порожній або не вдалося знайти треки.")
            elif info_dict['ie_key'] == 'YoutubeTab':
                playlist_url = Playlist(playlist_url)
                playlist_url_list = list(playlist_url)
                if len(playlist_url_list) >= 2:
                    for url in playlist_url_list[:25]:
                        await play_music(ctx, url)
                        await asyncio.sleep(1)
            else:
                await ctx.send("Не вдалося знайти треки в плейлисті.")
    except Exception as e:
        await ctx.send(f"Помилка при додаванні плейлисту: {e}")
        print(f"Помилка при додаванні плейлисту: {e}")


@bot.command(name="clear", aliases=["clean", "delete", 'видали', 'очисти'])
async def clear_messages(ctx, amount: int = 0):
    await ctx.channel.purge(limit=amount + 1)  # +1, щоб видалити ще й команду


if __name__ == '__main__':
    bot.run(TOKEN)
