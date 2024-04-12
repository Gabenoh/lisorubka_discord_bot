import discord
from discord.ext import commands
from yt_dlp import YoutubeDL
import asyncio
from token import TOKEN


intents = discord.Intents.all()  # allowing all intents
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
# Створення змінної для зберігання URL-адреси
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}


queue = asyncio.Queue()


async def connect_to_voice(ctx):
    """Функція для підключення до голосового каналу"""
    voice_channel = ctx.author.voice.channel
    if not voice_channel:
        await ctx.send("Ви повинні бути підключені до голосового каналу!")
    await voice_channel.connect()


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
                stream = info['requested_formats'][1]['url']
            else:
                info = ydl.extract_info(f"ytsearch:{url}", download=False)
                stream = info['entries'][0]['requested_formats'][1]['url']

            title = info['title']
            await ctx.send(f"Додано до черги: {title}")

            # Додавання URL-адреси відео до черги
            await queue.put(stream)

            # Якщо бот не відтворює відео наразі, почніть відтворення
            if not voice_client.is_playing():
                await play_next(ctx)

    except Exception as e:
        await ctx.send(f"Помилка під час відтворення музики: {e}")


async def play_next(ctx):
    voice_client = ctx.voice_client

    # Перевірка, чи аудіо не відтворюється
    if not voice_client.is_playing():
        # Якщо черга не порожня, відтворюємо наступне відео
        if not queue.empty():
            url = await queue.get()
            voice_client.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS),
                              after=lambda e: bot.loop.create_task(play_next(ctx)))
        else:
            # Якщо черга порожня, відключаємося від голосового каналу
            await voice_client.disconnect()
    else:
        voice_client.stop()
        await asyncio.sleep(5)
        if not queue.empty():
            url = await queue.get()
            voice_client.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS),
                              after=lambda e: bot.loop.create_task(play_next(ctx)))


@bot.command(name="play", aliases=['p', 'п', 'П', 'P'])
async def play(ctx, *, url):
    await play_music(ctx, url)


@bot.command(name="stop", aliases=['стоп', 'с', 's'])
async def stop(ctx):
    voice_client = ctx.voice_client
    if voice_client and voice_client.is_playing:
        voice_client.stop()
        await asyncio.sleep(2)
        await voice_client.disconnect()


@bot.command(name="next", aliases=['n', 'н', 'наступний'])
async def next(ctx):
    await play_next(ctx)


@bot.command(name="volume", aliases=['vol'])
async def set_volume(ctx, volume: int):
    voice_client = ctx.voice_client
    if voice_client:
        # Перевіряємо, чи вказане значення гучності знаходиться в межах від 0 до 100
        if 0 <= volume <= 100:
            # Перетворюємо значення гучності у діапазон від 0 до 1 (де 1 - максимальна гучність)
            volume = volume / 100
            # Встановлюємо гучність для голосового каналу
            voice_client.source.volume = volume
            await ctx.send(f"Гучність бота була встановлена на {volume * 100}%")
        else:
            await ctx.send("Будь ласка, вкажіть значення гучності від 0 до 100.")
    else:
        await ctx.send("Бот не підключений до голосового каналу.")


@bot.command(name='pause', aliases=['пауза'], help='This command pauses the song')
async def pause(ctx):
    voice_client = ctx.voice_client
    if voice_client is not None and voice_client.is_playing():
        await voice_client.pause()
    else:
        await ctx.send("На данний момент нічого не відтворюється")


@bot.command(name='resume', aliases=['старт', 'start'], help='Resumes the song')
async def resume(ctx):
    voice_client = ctx.voice_client
    if voice_client is not None and voice_client.is_paused():
        await voice_client.resume()
    else:
        await ctx.send("Бот нічого не відтворює. використай !play </url_for_music_video> команду")


if __name__ == '__main__':
    bot.run(TOKEN)
