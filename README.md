# ML VM for ABC Treebank on DepCCG
## 概要
ABC Treebankのパーザー
## インストール手順
1. Azure VMを作成
    <dl>
        <dt>Size</dt>
        <dd>NC6</dd>
        <dt>Image</dt>
        <dd>NVIDIA GPU Cloud 19.05.0</dd>
        <dt>Login</dt>
        <dd>SSH</dd>
    </dl>
1. VMを起動し，適当な端末からVMにSSH接続する
1. インストール
    - `sudo apt update && sudo apt upgrade`
    - （不足しているパッケージがあれば`apt`で適宜インストールすること）
    - docker-composeのバイナリを公式サイトからダウンロードし，パスが通っている適当なところ（例：`/usr/local/bin`）に置く．
    - Githubからのレポジトリのクローンのために，SSH鍵を作成
        レポジトリへの書き込みの権限を与えるか否かについては適当に決める．
        - SSH鍵のうち，秘密鍵は`~/.ssh/`に保存しておく
        - 公開鍵はGithubレポジトリのDeploy Keys"として登録をしてから，VM上から抹消する
    - sshデーモンを起動する
        ```sh
        eval `ssh-agent`
        ssh-add ~/.ssh/*
        ```
    - 本レポジトリをホームディレクトリにクローンする
        （パスを以後，`${ABC_DEPCCG_DOCKER_PATH}=~/abc-depccg-docker`として言及する）
1. データのアップロード
    SCPまたはSFTPを使い，以下のデータを指定の場所にアップロードする．
    ファイル名に注意．
    <dl>
        <dt>語彙モデル</dt>
        <dd>
            <a href="https://drive.google.com/file/d/1PwJYnegh9np6Nr_Wy1VJDutWIKu6rn7m/view?usp=sharing">吉川さんオリジナル</a>
            ：
            <code>${ABC_DEPCCG_DOCKER_PATH}/abc-depccg/lex-model-depccg-ja.tar.gz</code>
        </dd>
        <dt>単語ベクトル</dt>
        <dd><a herf="http://www.cl.ecei.tohoku.ac.jp/~m-suzuki/jawiki_vector/">日本語 Wikipedia エンティティベクトル</a>
        の最新版をダウンロード：
        <code>${ABC_DEPCCG_DOCKER_PATH}/abc-depccg/vector-wiija.tar.bz2</code>
        <dt>ABC Treebank</dt>
        <dd>空範疇をunary branchingにしたABC Treebankを適当に生成し，
            適当にアップロード：
            <code>~/abc-depccg/source/</code>
            に展開する．</dd>
    </dl>
1. Dockerイメージを構築する
    ```sh
    cd ${ABC_DEPCCG_DOCKER_PATH}
    sudo docker-compose build
    ```

## Dockerイメージ
パーザーの学習とパージングのための（唯一の）Dockerfileは，
`${ABC_DEPCCG_DOCKER_PATH}/abc-depccg/Dockerfile`である．
このDockerfileをもとに，`${ABC_DEPCCG_DOCKER_PATH}/docker-compose.yml`によって2つのイメージが定義される．
<dl>
    <dt>abc-depccg-train</dt>
    <dd>学習のためのイメージ</dd>
    <dt>abc-depccg-parse</dt>
    <dd>パージングの実行のためのイメージ</dd>
</dl>

2つのイメージにはともに，`ENTRYPOINT`が設定されている．
決まったプログラムのみが実行されるということが想定されている．

ボリュームマウントは以下のように指定されている：

|Path in VM|Path in Docker Containers|Availability|
|----------|-------------------------|------------|
|`~/abc-depccg-sources/current`|`/root/source`|abc-depccg-train|
|`~/abc-depccg-results`|`/root/results`|(BOTH)|

## 学習
```sh
cd ${ABC_DEPCCG_DOCKER_PATH}
sudo docker-compose run -d abc-depccg-train
```

コンテナID
（`${ABC_DEPCCG_DOCKER_CONTID}`と呼ぶこととする）
がSTDOUTに出力され，学習がバックグラウンドで開始される．

実行中のコンテナの状態を確認したいときには：
```sh
docker ps (-A)
```

学習の経過を見たいときには：
```sh
sudo docker logs --follow ${ABC_DEPCCG_DOCKER_CONTID}
```

GPUが動いているかどうか確認するときは：
```sh
nvidia-smi
```

学習（Azure VM NC6構成では，おおよそ8時間）が終えると，
結果物が`~/abc-depccg/result/（適当なタイムスタンプ）/`にて生成される．
そのフォルダ名のタイムスタンプ
（14桁；`${ABC_DEPCCG_DOCKER_RES_LATEST_TIMESTAMP}`と言及することにする）
をしっかりと把握しておく．

過去の学習の跡として，不必要なコンテナが残ることがある．
コンテナを残さないようにするためには，`docker run`の際にオプション `--rm` をつけるか，
`sudo docker container prune`を実行する．

## パージング
学習で得られたモデルを用いてパージングを試すには，
```sh
cd ${ABC_DEPCCG_DOCKER_PATH}
sudo docker-compose run abc-depccg-parse \
    --model /root/result/${ABC_DEPCCG_DOCKER_RES_LATEST_TIMESTAMP} \
    --input "何 か の 文"
```

バッチパージングをするためには，解析する文を（改行区切りで）何らかのファイルに保存した上で，
そのファイルの内容をパイプに流すことをする．
```sh
cat <files> | sudo docker-compose run abc-depccg-parse ...
```

他のオプション：
- `--format/-f <format>`：出力フォーマット
- `--tokenize`：形態素解析を前処理として行う