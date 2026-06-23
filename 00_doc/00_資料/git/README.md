# ■ GitHubアカウント作成
## 1. アカウント作成
下記URLを参考にGitHubアカウントを作成してください。  
参考：https://reffect.co.jp/html/create_github_account_first_time  
作成出来たら私までアカウント名を教えてください。

## 2. リポジトリ参加
TRYメール宛てにリポジトリ招待のメールが来ているので記載のURLにアクセスし、accept 後 yk-sasaki/study リポジトリにアクセスできることを確認して下さい。

# ■ Git環境構築
## 1. Git(ソースコードのバージョン管理ツール)のインストール
以下を参考にGit、TortoiseGit、日本語パッチ(任意)をインストール  
参考：https://sukkiri.jp/technologies/devtools/git/tortoisegit_win.html  

以下を参考に名前とメールアドレスを設定  
参考：https://qiita.com/mmake/items/63a869272c0dfa1d50a4#%E3%82%A4%E3%83%B3%E3%82%B9%E3%83%88%E3%83%BC%E3%83%AB%E5%BE%8C%E3%81%AB%E8%A8%AD%E5%AE%9A%E3%82%92%E5%A4%89%E6%9B%B4%E3%81%99%E3%82%8B%E6%96%B9%E6%B3%95

## 2. クローン用トークン作成
※トークン期限が切れた場合もこちらからやり直してください。  

以下を参考にトークンを作成　期限はとりあえず３か月程度で大丈夫です  
※作成したトークンは再度見ることができないので生成時にどこかにメモしておいてください  
参考：https://dev.classmethod.jp/articles/github-personal-access-tokens/

## 3. クローン(Gitに上がっているソースをローカルへダウンロード)
以下を参考に「C:\study」へクローンする  
参考：https://pasomaki.com/tortoisegit-clone/  
設定に必要な情報は以下参照  

【クローン設定内容】  
URL：https://[トークン]@github.com/yk-sasaki/study.git  
ディレクトリ：C:\study

# ■ 開発用エディタのインストール
必要に応じてインストールしてください。

## ◇ VSCodeのインストール
公式サイトよりVisual Studio Codeをインストールしてください  
URL：https://code.visualstudio.com/

## ◇ Eclipseのインストール
---

## ◇ sakuraエディタのインストール
---

# ■ VSCode 上での Git の使い方

## ◇ 自分の変更をGit上に上げるまでの手順

【手順】
1. pullで最新に更新(※pull成功時は「手順5.」へ)
2. stashで自分の変更を退避
3. 再度pullで最新に更新
4. stashの内容とローカルのソースを比較しマージ
5. addでコミットしたい対象のファイルをすべてステージに追加
6. コミットメッセージを入力しcommit
7. pushでGit上に反映
8. 不要になったstashを削除(※stashを使わなかった場合不要)

各コマンドの細かい説明は下記参照

## ◇ pull(プル)
Git上の最新ソースコードをローカルにDL  
※ローカル上で自分が編集した箇所とGit上で変更があった箇所がぶつかるとpullできません。  
　慣れるまではローカルで編集中のものをstashへ退避して編集が無い状態にしてからpullするといいです。  

【手順】
1. VS Codeの左下から３番目更新マークをクリック  
※「↓」横の数字が0より大きいとその件数分誰かがGitを更新しています

参考：https://zenn.dev/shimomura/articles/vs-code-git-github#pull(%E5%BC%95%E3%81%8F%2F%E5%BC%95%E3%81%A3%E5%BC%B5%E3%82%8B)

## ◇ add(アド)
変更したソースをステージに追加  

【手順】
1. VS Codeの左メニューからソース管理を選択
2. 変更欄に出ているファイルの右に表示されている「＋」を押下

参考：https://zenn.dev/shimomura/articles/vs-code-git-github#add(%E8%BF%BD%E5%8A%A0)

## ◇ commit(コミット)
addでステージに追加した内容をローカルのバージョン管理に反映  

【手順】
1. VS Codeの左メニューからソース管理を選択
2. メッセージと書いてある入力ボックスにコミットメッセージを記載  
例)　課題01-01追加
3. コミットボタンを押下

参考：https://zenn.dev/shimomura/articles/vs-code-git-github#commit(%E3%82%B3%E3%83%9F%E3%83%83%E3%83%88%2F%E9%A0%90%E3%81%91%E3%82%8B%2F%E5%A7%94%E3%81%AD%E3%82%8B)

## ◇ push(プッシュ)
commitでローカルのバージョン管理に反映したものをGit上に適用します  

【手順】
1. VS Codeの左下から３番目更新マークをクリック  
※「↑」数字が0より大きいとその件数分自分がcommitしています。  
　基本commitでため込まずにcommit、pushはセットで行います。

参考：https://zenn.dev/shimomura/articles/vs-code-git-github#push(%E6%8A%BC%E3%81%99%2F%E6%8A%BC%E3%81%97%E9%80%B2%E3%82%81%E3%82%8B)

## ◇ stash(スタッシュ)
緊急の修正など一時的に今の変更状態を記録する  
※ローカルで記憶するだけでバージョン管理上には反映されない

【stashへ追加手順】
1. VS Codeの左メニューからソース管理を選択
2. ソース管理のタイトル右に出てくる３点リーダー->スタッシュ->未追跡ファイルを含むを押下
3. VSCode上部に出てくる入力ボックスにstash名を記載して「Enter」押下

【stashの内容取り出し手順】
1. VS Codeの左メニューからソース管理を選択
2. ソース管理のタイトル右に出てくる３点リーダー->スタッシュ->スタッシュの適用を押下
3. VSCode上部に出てくる入力ボックスから戻したいstash名を選択して「Enter」押下

【不要になったstashの削除手順】
1. VS Codeの左メニューからソース管理を選択
2. ソース管理のタイトル右に出てくる３点リーダー->スタッシュ->スタッシュを削除するを押下
3. VSCode上部に出てくる入力ボックスから削除したいstash名を選択して「Enter」押下

参考：https://zenn.dev/shimomura/articles/vs-code-git-github#stash(%E9%9A%A0%E3%81%99%2F%E3%81%97%E3%81%BE%E3%81%86%2F%E8%93%84%E3%81%88%E3%82%8B)

## ◇ Git Graph(VSCodeの拡張機能)
使用する場合VSCodeの拡張機能で「Git Graph」検索してインストールしてください  
Gitの変更内容を時系列で参照することができます。(変更がわかりやすく便利なので入れましょう)

参照：https://qiita.com/y-tsutsu/items/2ba96b16b220fb5913be#git-graph%E6%8B%A1%E5%BC%B5%E6%A9%9F%E8%83%BD
