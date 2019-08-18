# ML VM for ABC Treebank on DepCCG

## 手順
1. Azure VMを作成：
  - Size: NC6
  - Image: NVIDIA GPU Cloud 19.05.0
  - Login: SSH
2. ログインを試みる
3. ログイン後：インストール
  - `sudo apt update && sudo apt upgrade`
  - 不足しているパッケージがあれば適宜インストール
  - docker-composeのバイナリを公式サイトからダウンロードし，インストール
  - 本レポジトリをダウンロード
  - `docker-compose build`
  - 学習データをscpなどでupし，`~/abc-treebank`に置く．
5. docker containerにアクセス：
  - `docker-compose up -d`
  - `docker exec -it abc-depccg_1 bash`
6. docker containerを閉じる：
  - `docker-compose down`