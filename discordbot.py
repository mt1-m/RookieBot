import discord

import requests
from bs4 import BeautifulSoup
import re
import random
import math
import json
from datetime import datetime, timezone, timedelta
from discord.ext import commands
from discord.ext import tasks
from discord import app_commands
from dotenv import load_dotenv
import os
import openai
import pickle
import deepl


# .env ファイルの読み込み
load_dotenv()

# APIキーの設定
openai.api_key = os.getenv("OPENAI_API_KEY")
translator = deepl.Translator(os.getenv("DEEPL_API_KEY"))
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

CHANNEL_ID = int(os.getenv("CHANNEL_ID", -1))  # 挨拶用
ANNOUNCE_CHANNEL_ID = int(os.getenv("ANNOUNCE_CHANNEL_ID", -1))  # AtCoderアナウンス用


client = commands.Bot(command_prefix="/", intents=discord.Intents.all())


"""Bot起動時に実行されるイベントハンドラ"""


@client.event
async def on_ready():
    print(os.getenv("OPENAI_API_KEY"))
    # 起動したらターミナルにログイン通知が表示される
    check_contests.start()
    await greet()  # 挨拶する非同期関数を実行
    # アクティビティを設定
    new_activity = f"テスト"
    await client.change_presence(activity=discord.Game(new_activity))
    await client.tree.sync()
    print("ログインしました")


# 返信する非同期関数を定義
async def reply(message):
    reply = f"{message.author.mention} What's up？"  # 返信メッセージの作成
    await message.channel.send(reply)  # 返信メッセージを送信


# 任意のチャンネルで挨拶する非同期関数を定義
async def greet():
    channel = client.get_channel(CHANNEL_ID)
    await channel.send("~~~ヾ(＾∇＾)Hello World♪")


async def get_latest_abc_number():
    url = "https://atcoder.jp/contests/archive?ratedType=1&category=0&keyword="
    response = requests.get(url)

    if response.status_code == 200:
        # ページの内容は response.text にあります
        page_content = response.text  # html

        # 正規表現で数字を抽出
        match = re.search(r"AtCoder Beginner Contest (\d+)", page_content)
        if match:
            contest_number = match.group(1)
            print(contest_number)
        else:
            print("数字が見つかりませんでした。")
    else:
        print(f"Error: {response.status_code}")
    return int(contest_number)


async def problem_list(link):
    print(link)
    response = requests.get(link)

    if response.status_code == 200:
        page_content = response.text
        soup = BeautifulSoup(page_content, "html.parser")
        # 配点テーブルから問題を抽出
        problem_table = soup.find("table", {"class": "table"})
        problems = [
            (row.find_all("td")[0].text.strip(), row.find_all("td")[1].text.strip())
            for row in problem_table.find_all("tr")[1:]
        ]
    else:
        print(f"Error: {response.status_code}")
    return problems


async def make_schedule():
    url = "https://atcoder.jp/contests/"
    response = requests.get(url)

    if response.status_code == 200:
        # ページの内容は response.text にあります
        page_content = response.text  # html
        # HTMLをBeautifulSoupオブジェクトにパース
        soup = BeautifulSoup(page_content, "html.parser")

        # 例: タイトルを取得
        title = soup.title
        # print(f"Title: {title.text}")

        # 予定されたコンテストのテーブルを選択
        contest_table = soup.find("div", {"id": "contest-table-upcoming"}).find("table")

        # テーブル内の各行を取得
        contest_rows = contest_table.find("tbody").find_all("tr")

        # コンテスト情報を格納するリスト
        contest_list = []

        # 各行から情報を抽出
        for row in contest_rows:
            columns = row.find_all(["td", "th"])
            # 開始時刻、コンテスト名、時間、Rated対象の情報を取得
            start_time = columns[0].text.strip()
            contest_name = columns[1].text.strip()
            contest_name = list(map(str, contest_name.split("\n")))[2]
            duration = columns[2].text.strip()
            rated = columns[3].text.strip()

            # 取得した情報を辞書に格納し、リストに追加
            contest_info = {
                "start_time": start_time,
                "contest_name": contest_name,
                "duration": duration,
                "rated": rated,
            }
            contest_list.append(contest_info)
        return contest_list
    else:
        print(f"Error: {response.status_code}")


async def randprob_by_color(prob, col, lower, upper):
    if col != -1 and col not in COLOR:
        return -999, -1
    tmp = []
    for p in prob:
        chosen_contest, *_ = map(str, p.split("_"))
        num = int(chosen_contest[3:])
        if num < lower or upper < num:
            continue
        if p not in data.keys():
            continue
        if "difficulty" not in data[p]:
            continue
        difficulty = data[p]["difficulty"]
        res = await calc_diff(difficulty)
        if res == col:
            tmp.append(p)
        elif col == -1:
            tmp.append(p)
    prob = tmp
    if len(prob) == 0:
        return -998, -1
    idx = random.randrange(len(prob))
    chosen_problem = prob[idx]
    col = await calc_diff(data[chosen_problem]["difficulty"])
    tmp = list(map(str, chosen_problem.split("_")))
    chosen_contest = "".join(tmp[:-1])
    print(chosen_contest)
    problem_link = (
        "https://atcoder.jp/contests/" + chosen_contest + "/tasks/" + chosen_problem
    )
    return col, problem_link


async def calc_diff(diff):
    if diff < 400:
        diff = round(400 / math.exp(1.0 - diff / 400))
    for i in range(len(COLOR) - 1):
        if diff < 400 * (i + 1):
            return COLOR[i]
    return COLOR[-1]


def load_json_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # エラーチェック

        # JSONデータを取得
        json_data = response.json()
        return json_data

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None


async def take_category():
    url = "https://atcoder-tags.herokuapp.com/explain"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("table")
    rows = table.find_all("tr")

    category = []
    description = []
    ignore = ["Other", "April-Fool", "Marathon"]
    category_dict = {}

    for row in rows:
        cells = row.find_all(["th", "td"])
        cat = cells[0].text.strip()
        cat_link = cells[0].find("a")["href"]
        desc = cells[1].text.strip()
        if cat in ignore:
            continue
        if cat == "Dynamic-Programming":
            cat = "DP"
        category.append(cat)
        desc = list(map(str, desc.split("（")))[0]
        desc = list(map(str, desc.split("(")))[0]
        description.append(desc)
        category_dict[desc] = cat_link
    return description, category_dict


async def take_prob_from_tags_url(url):
    # requestsを使用してWebページの内容を取得
    response = requests.get(url)

    # BeautifulSoupを使用してHTMLを解析
    soup = BeautifulSoup(response.text, "html.parser")

    # テーブル内の各行から問題IDを取得
    table = soup.find(
        "table", class_="table-borderd"
    )  # クラス名は正確に指定してください
    rows = table.find_all("tr")

    # 問題IDを格納するリスト
    problem_ids = []

    # 各行から問題IDを取り出してリストに格納
    for row in rows:
        cells = row.find_all("td", scope="row")
        if cells:
            problem_id = cells[1].text.strip()
            if not (problem_id[0] == "a" and problem_id[2] == "c"):
                continue
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
            categories.append(category_name)
            category_link = cells[0].find("a")["href"]
            categories_dict[category_name] = category_link
    return categories, categories_dict


async def translate(text, lang):
    return str(translator.translate_text(text, target_lang=lang))


async def make_response(prompt, load):
    # prompt_EN = await translate(prompt, "EN-US")
    prompt_EN = prompt
    if load:
        # 会話履歴を読み込み、ユーザーのプロンプトを追加
        # with open(f"./outputs/chat_history.pickle", "rb") as f:
        #     messages, total_tokens = pickle.load(f)
        # messages.append({"role": "user", "content": prompt_EN})

        messages = load
    else:
        # 新しい会話を開始
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt_EN},
        ]
    print(messages)

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo-16k-0613",
        # model="gpt-4-vision-preview",
        # model="gpt-4-1106-preview",
        messages=messages,
        temperature=0,
    )
    res = response.choices[0].message.content
    total_tokens = response.usage.total_tokens

    print(res)

    # 正規表現にマッチする部分を抜き出す
    pattern = r"```([^`]+)```"
    pattern = re.compile(pattern, re.DOTALL)
    quoted_texts = pattern.findall(res)
    result_list = re.split(pattern, res)
    result_list = [result_list[i] for i in range(len(result_list)) if i % 2 == 0]

    res_JA_v2 = []
    Lq = len(quoted_texts)
    if Lq < len(result_list):
        for i in range(Lq):
            res_JA_v2.append(await translate(result_list[i], "JA"))
            res_JA_v2.append("```" + quoted_texts[i] + "```")
        res_JA_v2.append(await translate(result_list[-1], "JA"))
    else:
        for i in range(Lq):
            res_JA_v2.append("```" + quoted_texts[i] + "```")
            res_JA_v2.append(await translate(result_list[i], "JA"))
    res_JA_v2 = "".join(res_JA_v2)

    # res_JA = await translate(res, "JA")
    # res_JA = re.sub(r"(`{2,})", r"```", res_JA)
    # print(type(res_JA))
    # print(res_JA)
    # print("sushi".index("s"))
    # idx1 = -1
    # idx2 = -1
    # if "「" in res_JA:
    #     idx1 = res_JA.index("「")
    # if "」" in res_JA:
    #     idx2 = res_JA.index("」")
    # if idx1 > idx2:
    #     res_JA = "「" + res_JA
    print(res_JA_v2)
    # 応答を保存
    await save_chat(
        messages=messages,
        new_message={"role": "assistant", "content": res},
        total_tokens=total_tokens,
    )
    return res_JA_v2, total_tokens


async def save_chat(messages, new_message, total_tokens):
    # 新しいメッセージを追加し、チャット履歴をファイルに保存
    messages.append(new_message)
    with open(f"./outputs/chat_history.pickle", "wb") as f:
        pickle.dump((messages, total_tokens), f)


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

my_commands = {
    "**/atcoder schedule**": "今後のスケジュールが表示される",
    "**/atcoder random_choice [コンテスト名] [色] [下限] [上限]**": "指定した条件でランダムに問題を出題 (色以降は任意)",
    "**/atcoder category [カテゴリ名] [サブカテゴリ] [色] [下限] [上限]**": "指定した条件でランダムに問題を出題 (色以降は任意)",
}
# JSONデータを読み込む
url = "https://kenkoooo.com/atcoder/resources/problem-models.json"
data = load_json_from_url(url)


ABC_prob = []
ARC_prob = []
AGC_prob = []
AHC_prob = []
else_prob = []
for key in data.keys():
    if "difficulty" not in data[key].keys():
        continue
    if key[:3] == "abc":
        ABC_prob.append(key)
    elif key[:3] == "arc":
        ARC_prob.append(key)
    elif key[:3] == "agc":
        AGC_prob.append(key)
    elif key[:3] == "ahc":
        AHC_prob.append(key)
    else:
        else_prob.append(key)


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
        if 291 <= time_difference.total_seconds() <= 300:  # 5分前になったら通知
            channel = client.get_channel(ANNOUNCE_CHANNEL_ID)
            await channel.send(f"{contest['contest_name']}が5分後に始まります！")


"""メッセージ受信時に実行されるイベントハンドラ"""


@client.event
async def on_message(message):
    args = message.content.split(" ")
    # メッセージ送信者がBotだった場合は無視する
    if message.author.bot:
        return

    if client.user in message.mentions:  # 話しかけられたかの判定
        await reply(message)  # 返信する非同期関数を実行

    if isinstance(message.channel, discord.Thread):
        thread_data = load_thread_data()
        thread_info = thread_data.get(message.channel.id)
        nushi = thread_info["owner"]
        if thread_info:

            # 過去のメッセージを表示
            messages = [
                msg
                async for msg in message.channel.history(limit=200, oldest_first=True)
            ]
            if messages[-1].author.name != nushi:
                print("無視")
                return

            log_data = [{"role": "system", "content": "You are a helpful assistant."}]
            # メッセージを出力
            for msg in messages[1:]:
                author = msg.author.name
                content = msg.content
                if author == "RookieBot":
                    log_data.append({"role": "system", "content": content})
                elif author == nushi:
                    log_data.append({"role": "user", "content": content})
            response, tokens = await make_response(None, log_data)

            await message.channel.send(response)

            print(f"{tokens} トークン使用({round(0.002*150*tokens/1000,5)}円相当)")

            print(
                f"Received message in thread '{thread_info['name']}' owned by user {thread_info['owner']}"
            )

    if args[0] == "/atcoder":
        if len(args) == 1:
            url = "https://atcoder.jp/"
            response = requests.get(url)

            if response.status_code == 200:
                # ページの内容は response.text にあります
                page_content = response.text  # html
                # HTMLをBeautifulSoupオブジェクトにパース
                soup = BeautifulSoup(page_content, "html.parser")

                # 例: タイトルを取得
                title = soup.title
                print(f"Title: {title.text}")
                await message.channel.send(f"Title: {title.text}")
            else:
                print(f"Error: {response.status_code}")
                await message.channel.send(f"Error: {response.status_code}")


"""リアクション追加時に実行されるイベントハンドラ"""


@client.event
async def on_reaction_add(reaction, user):
    pass


"""新規メンバー参加時に実行されるイベントハンドラ"""


@client.event
async def on_member_join(member):
    pass


"""メンバーのボイスチャンネル出入り時に実行されるイベントハンドラ"""


@client.event
async def on_voice_state_update(member, before, after):
    pass


# スレッド情報を保存する関数
def save_thread_data(thread_data, file_name):
    folder_path = "chat_log"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    file_path = os.path.join(folder_path, file_name)
    with open(file_path, "wb") as f:
        pickle.dump(thread_data, f)


# スレッド情報を読み込む関数
def load_thread_data(file_name):
    folder_path = "chat_log"
    file_path = os.path.join(folder_path, file_name)
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            thread_data = pickle.load(f)
        return thread_data
    else:
        return {}


# スレッド作成
@client.tree.command(name="chat", description="新しいスレッドを作成します。")
@app_commands.describe(title="作成するスレッド名")
async def chat(ctx, title: str):
    channel = ctx.channel
    thread = await channel.create_thread(
        name=title,
        reason="chatgpt会話用",
    )
    link = thread.mention

    # スレッド情報を保存
    thread_data = {}
    thread_data[thread.id] = {"name": title, "owner": ctx.user.name}
    save_thread_data(thread_data, f"{title}.pkl")

    res = load_thread_data(f"{title}.pkl")
    print(res)

    await thread.send(f"{ctx.user.mention} What's up？")
    await ctx.response.send_message(f"{link} こちらで会話してください")


@client.tree.command(name="delete_thread", description="指定したスレッドを削除します。")
@app_commands.describe(title="削除するスレッド名")
async def delete_thread(ctx, title: str):
    await ctx.response.defer()
    # スレッドを検索
    thread_to_delete = None
    for thread in ctx.guild.threads:
        if thread.name == title:
            thread_to_delete = thread
            break

    if thread_to_delete:
        # スレッドを削除
        await thread_to_delete.delete()

        # 対応する.pklファイルを削除
        file_name = f"{title}.pkl"
        file_path = os.path.join("chat_log", file_name)
        if os.path.exists(file_path):
            os.remove(file_path)

        await ctx.followup.send(f"スレッド '{title}' を削除しました。")
    else:
        await ctx.followup.send(f"スレッド '{title}' が見つかりませんでした。")


@client.tree.command(name="info")
async def infomation(ctx):
    res = []
    for cmd, content in my_commands.items():
        res.append(f"{cmd}: {content}\n")
    await ctx.response.send_message("".join(res))


@client.tree.command(name="chatgpt3-5_test")
@app_commands.describe(prompt="入力文")
async def chatgpt35(ctx, prompt: str):
    await ctx.response.defer()
    response, tokens = await make_response(prompt, False)
    res = (
        "入力："
        + prompt
        + "\n\n回答："
        + response
        + "\n\n"
        + f"{tokens} トークン使用({round(0.002*150*tokens/1000,5)}円相当)"
    )

    chunks = [res[i : i + 1980] for i in range(0, len(res), 1980)]
    ini = True
    for c in chunks:
        if ini:
            await ctx.followup.send(c)
            ini = False
        else:
            await ctx.channel.send(c)


@client.tree.command(name="chatgpt2")
async def chatgpt2(ctx):
    await ctx.response.send_message("実装中")


@client.tree.command(name="translate")
@discord.app_commands.choices(
    language=[
        discord.app_commands.Choice(name="English (American)", value="EN-US"),
        discord.app_commands.Choice(name="English (British)", value="EN-GB"),
        discord.app_commands.Choice(name="German", value="DE"),
        discord.app_commands.Choice(name="French", value="FR"),
        discord.app_commands.Choice(name="Chinese (simplified)", value="ZH"),
        discord.app_commands.Choice(name="Japanese", value="JA"),
    ]
)
@app_commands.describe(language="翻訳先の言語", text="翻訳する文章")
async def deepl_translate(ctx, language: str, text: str):
    prompt = text
    lang = language
    res = await translate(prompt, lang)
    await ctx.response.send_message(f"翻訳前： {prompt}\n翻訳後： {res}")


@client.tree.command(name="atcoder_schedule")
async def get_schedule(ctx):
    contest_list = await make_schedule()
    res = ""
    # 結果を表示
    res += "予定されたコンテスト--------------\n"
    print("予定されたコンテスト--------------")
    for contest in contest_list:
        resp = list(contest.values())
        res += " ".join(resp) + "\n"
        print(" ".join(resp))
    await ctx.response.send_message(res)


@discord.app_commands.choices(
    contest=[
        discord.app_commands.Choice(name="ABC", value="abc"),
        discord.app_commands.Choice(name="ARC", value="arc"),
        discord.app_commands.Choice(name="AGC", value="agc"),
        discord.app_commands.Choice(name="AHC", value="ahc"),
    ],
    color=[
        discord.app_commands.Choice(name="灰", value="gray"),
        discord.app_commands.Choice(name="茶", value="brown"),
        discord.app_commands.Choice(name="緑", value="green"),
        discord.app_commands.Choice(name="水", value="cyan"),
        discord.app_commands.Choice(name="青", value="blue"),
        discord.app_commands.Choice(name="黄", value="yellow"),
        discord.app_commands.Choice(name="橙", value="orange"),
        discord.app_commands.Choice(name="赤", value="red"),
        discord.app_commands.Choice(name="銅", value="bronze"),
        discord.app_commands.Choice(name="銀", value="silver"),
        discord.app_commands.Choice(name="金", value="gold"),
    ],
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
    if contest == "abc":
        prob = ABC_prob
    elif contest == "arc":
        prob = ARC_prob
    elif contest == "agc":
        prob = AGC_prob
    elif contest == "ahc":
        prob = AHC_prob
    else:
        await ctx.response.send_message("正しい種類を選択してください。")
        return

    if color is None:
        color = -1
    col, problem_link = await randprob_by_color(prob, color, lower_limit, upper_limit)
    if col == -999:
        await ctx.response.send_message("正しい色を選択してください。")
    elif col == -998:
        await ctx.response.send_message(
            "指定された条件を満たす問題は見つかりませんでした。"
        )
    else:
        res = emoji_color[col] + " " + col + "\n" + problem_link
        await ctx.response.send_message(res)


@discord.app_commands.choices(
    category=[
        discord.app_commands.Choice(name="イージー", value="イージー"),
        discord.app_commands.Choice(name="アドホック", value="アドホック"),
        discord.app_commands.Choice(name="探索アルゴリズム", value="探索アルゴリズム"),
        discord.app_commands.Choice(name="貪欲法", value="貪欲法"),
        discord.app_commands.Choice(
            name="文字列アルゴリズム", value="文字列アルゴリズム"
        ),
        discord.app_commands.Choice(name="数学", value="数学"),
        discord.app_commands.Choice(name="テクニック", value="テクニック"),
        discord.app_commands.Choice(name="構築", value="構築"),
        discord.app_commands.Choice(name="グラフ理論", value="グラフ理論"),
        discord.app_commands.Choice(name="動的計画法", value="動的計画法"),
        discord.app_commands.Choice(name="データ構造", value="データ構造"),
        discord.app_commands.Choice(name="ゲーム", value="ゲーム"),
        discord.app_commands.Choice(
            name="ネットワークフロー", value="ネットワークフロー"
        ),
        discord.app_commands.Choice(name="幾何学", value="幾何学"),
        discord.app_commands.Choice(name="インタラクティブ", value="インタラクティブ"),
    ],
    color=[
        discord.app_commands.Choice(name="灰", value="gray"),
        discord.app_commands.Choice(name="茶", value="brown"),
        discord.app_commands.Choice(name="緑", value="green"),
        discord.app_commands.Choice(name="水", value="cyan"),
        discord.app_commands.Choice(name="青", value="blue"),
        discord.app_commands.Choice(name="黄", value="yellow"),
        discord.app_commands.Choice(name="橙", value="orange"),
        discord.app_commands.Choice(name="赤", value="red"),
        discord.app_commands.Choice(name="銅", value="bronze"),
        discord.app_commands.Choice(name="銀", value="silver"),
        discord.app_commands.Choice(name="金", value="gold"),
    ],
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
        print(url)
        problem_ids = await take_prob_from_tags_url(url)

        if color is None:
            color = -1
        col, problem_link = await randprob_by_color(
            problem_ids, color, lower_limit, upper_limit
        )
        if col == -999:
            await ctx.followup.send("正しい色を選択してください。")
            return
        elif col == -998:
            await ctx.followup.send(
                "指定された条件を満たす問題は見つかりませんでした。"
            )
            return
        else:
            res = emoji_color[col] + " " + col + "\n" + problem_link
            await ctx.followup.send(res)
            return

    else:
        problem_ids = await take_prob_from_tags_url(url)

        if color is None:
            color = -1
        col, problem_link = await randprob_by_color(
            problem_ids, color, lower_limit, upper_limit
        )
        if col == -999:
            await ctx.followup.send("正しい色を選択してください。")
            return
        elif col == -998:
            await ctx.followup.send(
                "指定された条件を満たす問題は見つかりませんでした。"
            )
            return
        else:
            res = emoji_color[col] + " " + col + "\n" + problem_link
            await ctx.followup.send(res)
            return


# Botの起動とDiscordサーバーへの接続
client.run(TOKEN)
