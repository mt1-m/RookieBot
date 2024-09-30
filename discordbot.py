import os
import math
import json
import random
import pickle
import requests
import discord
import openai
import re
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv
import deepl

# .env ファイルの読み込み
load_dotenv()

# APIキーの設定
openai.api_key = os.getenv("OPENAI_API_KEY")
translator = deepl.Translator(os.getenv("DEEPL_API_KEY"))
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", -1))  # 挨拶用
ANNOUNCE_CHANNEL_ID = int(os.getenv("ANNOUNCE_CHANNEL_ID", -1))  # AtCoderアナウンス用

# Discordクライアントの設定
client = commands.Bot(command_prefix="/", intents=discord.Intents.all())

# 定数の定義
COLOR = [
    "gray",
    "brown",
    "green",
    "cyan",
    "blue",
    "yellow",
    "orange",
    "red",
    "bronze",
    "silver",
    "gold",
]

emoji_color = {
    "gray": ":grey_heart:",
    "brown": ":brown_heart:",
    "green": ":green_heart:",
    "cyan": ":light_blue_heart:",
    "blue": ":blue_heart:",
    "yellow": ":yellow_heart:",
    "orange": ":orange_heart:",
    "red": ":red_heart:",
    "bronze": ":beating_heart:",
    "silver": ":white_heart:",
    "gold": ":sparkling_heart:",
}

# コマンドの情報を格納するグローバル変数
my_commands = {
    "/info": "利用可能なコマンドの一覧と説明を表示します。",
    "/chat [タイトル]": "新しいスレッドを作成します。(ここでは)",
    "/delete_thread [タイトル]": "指定したスレッドを削除します。",
    "/chatgpt4 [プロンプト]": "GPT-4を使用してプロンプトに応答します。",
    "/dall-e3 [プロンプト]": "DALL·E 3を使用して画像を生成します。",
    "/translate [言語] [テキスト]": "テキストを指定した言語に翻訳します。",
    "/atcoder_schedule": "今後のAtCoderのコンテストスケジュールを表示します。",
    "/atcoder_random [コンテスト] [色] [下限] [上限]": "指定した条件でランダムに問題を出題します。",
    "/atcoder_category [カテゴリ] [サブカテゴリ] [色] [下限] [上限]": "指定したカテゴリから問題を出題します。",
}

# 関数定義セクション


def load_json_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None


async def make_schedule():
    url = "https://atcoder.jp/contests/"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    contest_table = soup.find("div", {"id": "contest-table-upcoming"}).find("table")
    contest_rows = contest_table.find("tbody").find_all("tr")
    contest_list = []
    for row in contest_rows:
        columns = row.find_all(["td", "th"])
        start_time = columns[0].text.strip()
        contest_name = columns[1].text.strip().split("\n")[2]
        duration = columns[2].text.strip()
        rated = columns[3].text.strip()
        contest_info = {
            "start_time": start_time,
            "contest_name": contest_name,
            "duration": duration,
            "rated": rated,
        }
        contest_list.append(contest_info)
    return contest_list


async def randprob_by_color(prob, col, lower, upper):
    if col != -1 and col not in COLOR:
        return -999, -1
    tmp = []
    for p in prob:
        chosen_contest = p.split("_")[0]
        num = int(chosen_contest[3:])
        if not (lower <= num <= upper):
            continue
        if p not in data or "difficulty" not in data[p]:
            continue
        difficulty = data[p]["difficulty"]
        res = await calc_diff(difficulty)
        if res == col or col == -1:
            tmp.append(p)
    if not tmp:
        return -998, -1
    chosen_problem = random.choice(tmp)
    col = await calc_diff(data[chosen_problem]["difficulty"])
    chosen_contest = "".join(chosen_problem.split("_")[:-1])
    problem_link = (
        f"https://atcoder.jp/contests/{chosen_contest}/tasks/{chosen_problem}"
    )
    return col, problem_link


async def calc_diff(diff):
    if diff < 400:
        diff = round(400 / math.exp(1.0 - diff / 400))
    for i in range(len(COLOR) - 1):
        if diff < 400 * (i + 1):
            return COLOR[i]
    return COLOR[-1]


async def take_category():
    url = "https://atcoder-tags.herokuapp.com/explain"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table")
    rows = table.find_all("tr")
    description = []
    category_dict = {}
    ignore = ["Other", "April-Fool", "Marathon"]
    for row in rows:
        cells = row.find_all(["th", "td"])
        cat = cells[0].text.strip()
        cat_link = cells[0].find("a")["href"]
        desc = cells[1].text.strip().split("（")[0].split("(")[0]
        if cat in ignore:
            continue
        if cat == "Dynamic-Programming":
            cat = "DP"
        description.append(desc)
        category_dict[desc] = cat_link
    return description, category_dict


async def take_prob_from_tags_url(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", class_="table-borderd")
    rows = table.find_all("tr")
    problem_ids = []
    for row in rows:
        cells = row.find_all("td", scope="row")
        if cells:
            problem_id = cells[1].text.strip()
            if problem_id[0] == "a" and problem_id[2] == "c":
                problem_ids.append(problem_id)
    return problem_ids


async def take_sub_category(response):
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", class_="table-borderd")
    rows = table.find_all("tr")
    categories = []
    categories_dict = {}
    for row in rows:
        cells = row.find_all("th", scope="row")
        if cells:
            category_name = cells[0].text.strip()
            category_link = cells[0].find("a")["href"]
            categories.append(category_name)
            categories_dict[category_name] = category_link
    return categories, categories_dict


async def translate(text, lang):
    return str(translator.translate_text(text, target_lang=lang))


async def generate_images(prompt):
    response = openai.images.generate(
        prompt=prompt, n=1, size="1024x1024", response_format="url", model="dall-e-3"
    )
    image_url = response.data[0].url
    return image_url


async def make_response(prompt, load):
    prompt_EN = prompt
    messages = (
        load
        if load
        else [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt_EN},
        ]
    )
    response = openai.ChatCompletion.acreate(
        model="gpt-4",
        messages=messages,
        temperature=0,
    )
    res = response.choices[0].message.content
    total_tokens = response.usage.total_tokens
    pattern = re.compile(r"```([^`]+)```", re.DOTALL)
    quoted_texts = pattern.findall(res)
    result_list = re.split(pattern, res)
    result_list = [result_list[i] for i in range(len(result_list)) if i % 2 == 0]
    res_JA_v2 = []
    Lq = len(quoted_texts)
    if Lq < len(result_list):
        for i in range(Lq):
            res_JA_v2.append(await translate(result_list[i], "JA"))
            res_JA_v2.append(f"```{quoted_texts[i]}```")
        res_JA_v2.append(await translate(result_list[-1], "JA"))
    else:
        for i in range(Lq):
            res_JA_v2.append(f"```{quoted_texts[i]}```")
            res_JA_v2.append(await translate(result_list[i], "JA"))
    res_JA_v2 = "".join(res_JA_v2)
    return res, res_JA_v2, total_tokens


def load_chat_data(chat_name):
    file_path = os.path.join("chat_log", chat_name)
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        with open(file_path, "rb") as f:
            return pickle.load(f)
    return []


def save_chat_data(add_thread_data, chat_name):
    existing_data = load_chat_data(chat_name)
    existing_data.append(add_thread_data)
    file_path = os.path.join("chat_log", chat_name)
    with open(file_path, "wb") as f:
        pickle.dump(existing_data, f)


def load_thread_data():
    file_path = "threads_data.pkl"
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        with open(file_path, "rb") as f:
            return pickle.load(f)
    return {}


def save_thread_data(add_thread_data):
    existing_data = load_thread_data()
    existing_data.update(add_thread_data)
    with open("threads_data.pkl", "wb") as f:
        pickle.dump(existing_data, f)


async def reply(message):
    reply = f"{message.author.mention} What's up？"
    await message.channel.send(reply)


# JSONデータを読み込む
url = "https://kenkoooo.com/atcoder/resources/problem-models.json"
data = load_json_from_url(url)

# 問題を分類
ABC_prob, ARC_prob, AGC_prob, AHC_prob, else_prob = [], [], [], [], []
for key in data.keys():
    if "difficulty" not in data[key]:
        continue
    if key.startswith("abc"):
        ABC_prob.append(key)
    elif key.startswith("arc"):
        ARC_prob.append(key)
    elif key.startswith("agc"):
        AGC_prob.append(key)
    elif key.startswith("ahc"):
        AHC_prob.append(key)
    else:
        else_prob.append(key)

# イベントハンドラセクション


@client.event
async def on_ready():
    print("Botがログインしました")
    check_contests.start()
    await greet()
    await client.tree.sync()


@tasks.loop(seconds=10)
async def check_contests():
    now = datetime.now(timezone(timedelta(hours=9)))
    contests = await make_schedule()
    dt_format = "%Y-%m-%d %H:%M:%S%z"
    for contest in contests:
        contest_datetime = datetime.strptime(contest["start_time"], dt_format)
        contest_datetime_local = contest_datetime.astimezone(
            timezone(timedelta(hours=9))
        )
        time_difference = contest_datetime_local - now
        if 291 <= time_difference.total_seconds() <= 300:
            channel = client.get_channel(ANNOUNCE_CHANNEL_ID)
            await channel.send(f"{contest['contest_name']}が5分後に始まります！")


async def greet():
    channel = client.get_channel(CHANNEL_ID)
    await channel.send("~~~ヾ(＾∇＾)Hello World♪")


@client.event
async def on_message(message):
    if message.author.bot:
        return
    if client.user in message.mentions:
        await reply(message)
    if isinstance(message.channel, discord.Thread):
        thread_data = load_thread_data()
        thread_info = thread_data.get(message.channel.id)
        if thread_info:
            nushi = thread_info["owner"]
            if message.author.name != nushi:
                return
            loading_message = await message.channel.send("返答生成中...")
            chat_name = f"{message.channel.name}.pkl"
            prompt_EN = await translate(message.content, "EN-US")
            save_chat_data({"role": "user", "content": prompt_EN}, chat_name)
            log_data = load_chat_data(chat_name)
            EN_response, response, tokens = await make_response(None, log_data)
            save_chat_data({"role": "system", "content": EN_response}, chat_name)
            cost = round(20 * 150 * 1.50 * tokens / 1_000_000, 5)
            await loading_message.edit(
                content=f"{response}\n{tokens} トークン使用({cost}円相当)"
            )
    await client.process_commands(message)


# コマンド定義セクション


@client.tree.command(name="chat", description="新しいスレッドを作成します。")
@app_commands.describe(title="作成するスレッド名")
async def chat(ctx, title: str):
    await ctx.response.defer()
    if any(thread.name == title for thread in ctx.guild.threads):
        await ctx.followup.send(f"すでに '{title}' という名前のスレッドが存在します。")
        return
    channel = ctx.channel
    thread = await channel.create_thread(
        name=title,
        reason="chatgpt会話用",
    )
    link = thread.mention
    thread_data = {
        thread.id: {
            "name": title,
            "owner": ctx.user.name,
            "channel_id": channel.id,
        }
    }
    file_name = f"{title}.pkl"
    init_thread_data = {"role": "system", "content": "You are a helpful assistant."}
    save_chat_data(init_thread_data, file_name)
    save_thread_data(thread_data)
    await thread.send(f"{ctx.user.mention} ハローワールド！")
    await ctx.followup.send(f"{link} こちらで会話してください")


@client.tree.command(name="delete_thread", description="指定したスレッドを削除します。")
@app_commands.describe(title="削除するスレッド名")
async def delete_thread(ctx, title: str):
    await ctx.response.defer()
    thread_to_delete = next(
        (thread for thread in ctx.guild.threads if thread.name == title), None
    )
    if not thread_to_delete:
        await ctx.followup.send(f"スレッド '{title}' が見つかりませんでした。")
        return
    thread_data = load_thread_data()
    for thread_id, data in list(thread_data.items()):
        if data["name"] == title and data["channel_id"] == ctx.channel_id:
            if data["owner"] != str(ctx.user):
                await ctx.followup.send("このスレッドを削除する権限がありません。")
                return
            del thread_data[thread_id]
            break
    save_thread_data(thread_data)
    await thread_to_delete.delete()
    file_path = os.path.join("chat_log", f"{title}.pkl")
    if os.path.exists(file_path):
        os.remove(file_path)
    await ctx.followup.send(f"スレッド '{title}' を削除しました。")


@client.tree.command(name="info", description="利用可能なコマンドの一覧を表示します。")
async def information(ctx):
    res = "**利用可能なコマンド一覧：**\n"
    for cmd, description in my_commands.items():
        res += f"{cmd}: {description}\n"
    await ctx.response.send_message(res)


@client.tree.command(name="chatgpt4")
@app_commands.describe(prompt="入力文")
async def chatgpt40(ctx, prompt: str):
    await ctx.response.defer()
    _, response, tokens = await make_response(prompt, False)
    res = f"入力：{prompt}\n\n回答：{response}\n\n{tokens} トークン使用"
    chunks = [res[i : i + 1980] for i in range(0, len(res), 1980)]
    for i, chunk in enumerate(chunks):
        if i == 0:
            await ctx.followup.send(chunk)
        else:
            await ctx.channel.send(chunk)


@client.tree.command(name="dall-e3")
@app_commands.describe(prompt="画像生成のプロンプト")
async def DALLE3(ctx, prompt: str):
    await ctx.response.defer()
    image_url = await generate_images(prompt)
    await ctx.followup.send(f"プロンプト: {prompt}")
    await ctx.followup.send(image_url)


@client.tree.command(name="translate")
@discord.app_commands.choices(
    language=[
        discord.app_commands.Choice(name="English (American)", value="EN-US"),
        discord.app_commands.Choice(name="English (British)", value="EN-GB"),
        discord.app_commands.Choice(name="German", value="DE"),
        discord.app_commands.Choice(name="French", value="FR"),
        discord.app_commands.Choice(name="Spanish", value="ES"),
        discord.app_commands.Choice(name="Chinese (simplified)", value="ZH"),
        discord.app_commands.Choice(name="Japanese", value="JA"),
    ]
)
@app_commands.describe(language="翻訳先の言語", text="翻訳する文章")
async def deepl_translate(ctx, language: str, text: str):
    res = await translate(text, language)
    await ctx.response.send_message(f"翻訳前：{text}\n翻訳後：{res}")


@client.tree.command(name="atcoder_schedule")
async def get_schedule(ctx):
    contest_list = await make_schedule()
    res = "予定されたコンテスト--------------\n"
    res += "\n".join(" ".join(contest.values()) for contest in contest_list)
    await ctx.response.send_message(res)


# コマンド内でカテゴリーを取得するためのオートコンプリート関数
async def category_autocomplete(
    interaction: discord.Interaction,
    current: str,
):
    description, _ = await take_category()
    return [
        app_commands.Choice(name=desc, value=desc)
        for desc in description
        if current.lower() in desc.lower()
    ]


@discord.app_commands.choices(
    color=[discord.app_commands.Choice(name=color, value=color) for color in COLOR],
)
@app_commands.describe(
    category="分野",
    sub_category="区分",
    color="難易度",
    lower_limit="コンテスト番号の下限",
    upper_limit="コンテスト番号の上限",
)
@client.tree.command(name="atcoder_category")
async def get_categProb(
    ctx,
    category: str,
    sub_category: str = None,
    color: str = None,
    lower_limit: int = 0,
    upper_limit: int = 10000,
):
    await ctx.response.defer()
    description, category_dict = await take_category()
    if category not in description:
        res = "この中のカテゴリーから選択してください：\n" + "　".join(description)
        await ctx.followup.send(res)
        return
    url = "https://atcoder-tags.herokuapp.com" + category_dict[category]
    response = requests.get(url)
    if "/tags" in url:
        categories, categories_dict = await take_sub_category(response)
        if sub_category not in categories:
            res = "この中のサブカテゴリーから選択してください：\n" + "　".join(
                categories
            )
            await ctx.followup.send(res)
            return
        url = "https://atcoder-tags.herokuapp.com" + categories_dict[sub_category]
        problem_ids = await take_prob_from_tags_url(url)
    else:
        problem_ids = await take_prob_from_tags_url(url)
    color = color or -1
    col, problem_link = await randprob_by_color(
        problem_ids, color, lower_limit, upper_limit
    )
    if col == -999:
        await ctx.followup.send("正しい色を選択してください。")
    elif col == -998:
        await ctx.followup.send("指定された条件を満たす問題は見つかりませんでした。")
    else:
        res = f"{emoji_color[col]} {col}\n{problem_link}"
        await ctx.followup.send(res)


@get_categProb.autocomplete("category")
async def category_autocomplete_handler(
    interaction: discord.Interaction,
    current: str,
):
    return await category_autocomplete(interaction, current)


@discord.app_commands.choices(
    contest=[
        discord.app_commands.Choice(name="ABC", value="abc"),
        discord.app_commands.Choice(name="ARC", value="arc"),
        discord.app_commands.Choice(name="AGC", value="agc"),
        discord.app_commands.Choice(name="AHC", value="ahc"),
    ],
    color=[discord.app_commands.Choice(name=color, value=color) for color in COLOR],
)
@app_commands.describe(
    contest="コンテストの種類",
    color="難易度",
    lower_limit="コンテスト番号の下限",
    upper_limit="コンテスト番号の上限",
)
@client.tree.command(name="atcoder_random")
async def get_randomProb(
    ctx,
    contest: str,
    color: str = None,
    lower_limit: int = 0,
    upper_limit: int = 10000,
):
    prob = {
        "abc": ABC_prob,
        "arc": ARC_prob,
        "agc": AGC_prob,
        "ahc": AHC_prob,
    }.get(contest)
    if prob is None:
        await ctx.response.send_message("正しい種類を選択してください。")
        return
    color = color or -1
    col, problem_link = await randprob_by_color(prob, color, lower_limit, upper_limit)
    if col == -999:
        await ctx.response.send_message("正しい色を選択してください。")
    elif col == -998:
        await ctx.response.send_message(
            "指定された条件を満たす問題は見つかりませんでした。"
        )
    else:
        res = f"{emoji_color[col]} {col}\n{problem_link}"
        await ctx.response.send_message(res)


# Botの起動
client.run(TOKEN)
