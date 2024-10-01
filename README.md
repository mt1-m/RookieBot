# RookieBot

RookieBot は、Discord サーバーをより便利で楽しいものにするための多機能な Discord ボットです。AtCoder のコンテスト情報の提供や問題のランダム出題、ChatGPT との連携、DALL·E を使用した画像生成、DeepL を用いた翻訳機能など、多彩な機能を備えています。

## 特徴

- **AtCoder コンテスト通知**: 今後の AtCoder コンテストのスケジュールを表示し、開始5分前にリマインダーを送信します。
- **ランダム問題出題**: 指定した条件（コンテスト種類、難易度カラー、番号範囲）に基づいて、AtCoder の問題をランダムに出題します。
- **カテゴリ別問題出題**: 特定のカテゴリやサブカテゴリから問題をランダムに選択して出題します。
- **ChatGPT 連携**: Discord スレッド内で OpenAI の GPT-4 モデルと対話できます。
- **DALL·E 画像生成**: OpenAI の DALL·E を使用して、ユーザーのプロンプトに基づいた画像を生成します。
- **翻訳機能**: DeepL を利用して、テキストを複数の言語間で翻訳します。

## インストール

### 必要要件

- Python 3.9 以上
- Discord アカウントとボットを追加可能な Discord サーバー
- OpenAI API キー
- DeepL API キー
- Discord ボットのトークン

### セットアップ手順

1. **リポジトリをクローン**

   ```bash
   git clone https://github.com/あなたのユーザー名/RookieBot.git
   cd RookieBot
依存関係をインストール

bash
コードをコピーする
pip install -r requirements.txt
.env ファイルを作成

プロジェクトのルートディレクトリに .env ファイルを作成し、以下の変数を設定します。

env
コードをコピーする
DISCORD_BOT_TOKEN=あなたのディスコードボットのトークン
OPENAI_API_KEY=あなたのOpenAI APIキー
DEEPL_API_KEY=あなたのDeepL APIキー
CHANNEL_ID=挨拶メッセージを送信するチャンネルのID
ANNOUNCE_CHANNEL_ID=AtCoderアナウンスを送信するチャンネルのID
ボットを実行

bash
コードをコピーする
python discordbot.py
設定
DISCORD_BOT_TOKEN: Discord ボットのトークン。
OPENAI_API_KEY: OpenAI の API キー（GPT-4 や DALL·E にアクセスするため）。
DEEPL_API_KEY: DeepL の API キー（翻訳機能に使用）。
CHANNEL_ID: ボットが起動時に挨拶メッセージを送信するチャンネルの ID。
ANNOUNCE_CHANNEL_ID: AtCoder のコンテスト情報を通知するチャンネルの ID。
使い方
ボットを実行し、Discord サーバーに追加したら、以下のコマンドを使用できます。

一般コマンド
/info: 利用可能なコマンドの一覧と説明を表示します。
/translate [言語] [テキスト]: DeepL を使用して、指定した言語にテキストを翻訳します。
ChatGPT 連携
/chat [タイトル]: ChatGPT と対話するための新しいスレッドを作成します。
/delete_thread [タイトル]: 自分が作成したスレッドを削除します。
ChatGPT スレッド内: スレッド内でメッセージを送信すると、GPT-4 が応答します。
DALL·E 画像生成
/dall-e3 [プロンプト]: DALL·E を使用して、プロンプトに基づいた画像を生成します。
AtCoder コマンド
/atcoder_schedule: 今後の AtCoder コンテストのスケジュールを表示します。
/atcoder_random [コンテスト] [色] [下限] [上限]: 指定した条件でランダムに AtCoder の問題を出題します。
/atcoder_category [カテゴリ] [サブカテゴリ] [色] [下限] [上限]: 指定したカテゴリやサブカテゴリから問題を出題します。
コマンド例
/chatgpt4 最近の天気はどうですか？: GPT-4 に最近の天気について質問します。
/translate EN こんにちは、元気ですか？: 「こんにちは、元気ですか？」を英語に翻訳します。
/dall-e3 夕日に照らされた未来都市の風景: 指定したプロンプトに基づいて画像を生成します。
/atcoder_random abc green 100 200: ABC コンテストの問題番号100から200までの緑色の問題をランダムに出題します。
コマンド一覧
コマンド	説明
/info	利用可能なコマンドの一覧と説明を表示します。
/chat [タイトル]	新しいスレッドを作成し、ChatGPT と対話します。
/delete_thread [タイトル]	自分が作成したスレッドを削除します。
/chatgpt4 [プロンプト]	GPT-4 がプロンプトに応答します。
/dall-e3 [プロンプト]	DALL·E を使用して画像を生成します。
/translate [言語] [テキスト]	テキストを指定した言語に翻訳します。
/atcoder_schedule	今後の AtCoder コンテストのスケジュールを表示します。
/atcoder_random [コンテスト] [色] [下限] [上限]	指定した条件で問題をランダムに出題します。
/atcoder_category [カテゴリ] [サブカテゴリ] [色] [下限] [上限]	指定したカテゴリから問題をランダムに出題します。
※ [ ] で囲まれた項目は任意のパラメータです。

貢献
貢献は大歓迎です！問題の報告や機能の提案、プルリクエストなど、お気軽にご参加ください。

ライセンス
このプロジェクトは MIT ライセンスの下で公開されています。詳細は LICENSE ファイルをご覧ください。
