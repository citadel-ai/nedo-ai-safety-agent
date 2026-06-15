# NEDO AI Safety Agent

This repository contains two components produced as part of a research effort into the risks and barriers of developing modern LLM-based applications. The findings are included in the publicly available report:

> **生成 AI 実践ガイドと企業事例集 〜 品質・安全性・ガバナンスを統合し本番運用へ導くフレームワーク 〜**

## Repository Structure

### [`datasets/`](./datasets/)

A publicly available dataset of files scraped from municipal government websites. Every file included has explicit copyright approval from its respective source. Files deemed "problematic" from a rights perspective have been excluded.

### [`demo/`](./demo/)

A sample chatbot application built on top of the dataset above, developed to study the practical challenges of building a production-grade LLM application — covering quality, safety, and governance concerns.

> **Note:** The live demo uses a significantly larger corpus than what is available in the `datasets/` folder, due to differences between usage permissions and redistribution permissions for the underlying data.

## Important Notice

- The data was compiled based on information available as of **February 2026** and should be used with the understanding that it may not be up to date.
- Users should verify chatbot answers by checking the relevant official websites themselves.
- There are no plans to update the data.
- Contacting individual municipalities about information from this tool is strictly prohibited.

## License

The chatbot source code under [`demo/`](./demo/) is released under the [MIT License](./demo/LICENSE).

The datasets under [`datasets/`](./datasets/) come from two different types of sources, each with its own terms:

- **Municipal datasets** (data sourced from local governments such as wards (区) and cities (市)): Included strictly as a reference to allow the code in this repository to be run locally. Any other use or public redistribution is **not permitted**. If you wish to use these datasets for any other purpose, you must obtain permission directly from each municipality. All rights, including copyright, remain with the respective municipalities.
- **Ministry datasets** (data sourced from national government ministries): Licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) and may be used as-is.

Please open each subfolder for more details.

# NEDO AI 安全性エージェント

本リポジトリには、最新の LLM ベースアプリケーション開発におけるリスクと障壁を調査する研究活動の一環として作成された、2 つのコンポーネントが含まれています。調査結果は以下の公開レポートに掲載されています：

> **生成 AI 実践ガイドと企業事例集 〜 品質・安全性・ガバナンスを統合し本番運用へ導くフレームワーク 〜**

## リポジトリ構成

### [`datasets/`](./datasets/)

自治体ウェブサイトからスクレイピングしたファイルの公開データセットです。収録されているすべてのファイルは、各提供元から明示的な著作権許諾を得ています。著作権の許諾を確認できなかったファイルは除外しています。

### [`demo/`](./demo/)

上記データセットを基に構築されたサンプルチャットボットアプリケーションです。本番レベルの LLM アプリケーション開発における品質・安全性・ガバナンスの実践的な課題を研究する目的で開発されました。

> **注意：** ライブデモでは、データの利用許諾と再配布許諾の違いにより、`datasets/` フォルダで公開されているデータより多くのデータを使用しています。

## ご利用上の注意

- 本データは **2026年2月時点** の情報を基に作成されています。最新の状況を反映していない可能性があるため、あらかじめご了承のうえご利用ください。
- チャットボットの回答内容については、必ず利用者ご自身で関連する公式ホームページをご確認ください。
- 本データについて、今後更新を行う予定はありません。
- 本ツールの出力内容に関して、各自治体へ問い合わせることは固く禁止します。

## ライセンス

[`demo/`](./demo/) 配下のチャットボットソースコードは [MIT ライセンス](./demo/LICENSE)で提供されています。

[`datasets/`](./datasets/) 配下のデータセットは提供元によって取扱いが異なります：

- **自治体のデータセット**（区・市など地方自治体が提供元のデータ）: 本リポジトリのコードを手元で動かすための参考資料としてのみ提供されています。これらの資料に関する著作権その他の権利は、各自治体に帰属しており、それ以外の用途での利用は**認められません**。他の用途で利用したい場合は、著作権者である各自治体へ個別に許諾を得てください。
- **省庁のデータセット**（国の省庁が提供元のデータ）: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) ライセンスのもとで提供されており、そのままご利用いただけます。

詳細については、各サブフォルダを開いてご確認ください。
