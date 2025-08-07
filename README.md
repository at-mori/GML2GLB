# WebAR Terrain Model Generator

このプロジェクトは、国土地理院の GML 形式の標高データ（10m メッシュ）を読み込み、指定領域を切り出して 3D 地形モデル（glb形式）としてエクスポートする Python スクリプトです。AR.js + A-Frame を使ったマーカーベースの WebAR 表示を目的としており、HTML ファイルの例も提供します。

## ■ サンプル

- [AR技術を活用した立体感覚の涵養を目的とする地学教材の開発／火山の形状（AR教材のサンプル）](https://robo.mydns.jp/WebAR/index.html#kazan)

## ■ 必要な環境

- Python 3.8 以上
- 利用するモジュール:  
  `sys`, `os`, `numpy`, `xml`, `collections`, `trimesh`, `scipy`

## ■ インストール手順

```bash
git clone https://github.com/at-mori/GML2GLB.git
cd GML2GLB
```

## ■ 使用方法

### 1. データの取得

[基盤地図情報ダウンロードサービス（数値標高モデル）](https://service.gsi.go.jp/kiban/app/map/?search=dem) から 10m メッシュ（区分：10B）の GML データをダウンロードします。
<img src="https://robo.mydns.jp/WebAR/figs/ChiriinPage.jpg" width=256>
- 山頂を中心に約 30km 四方（例：3×3タイル）のデータが必要です。  
- 境界に近い山頂の場合は、複数の GML ファイルを同時に指定してください。  
- ダウンロードにはユーザー登録が必要です。
- 現状では、グリッドを3つごとに選んで間引いています。
- 水平方向に対して、高さ方向は1.5倍に強調されています。
- 緯度の違いによる補正は精密ではありません。

### 2. GMLファイルを展開

ダウンロード後、ZIP を解凍すると `FG-GML-xxxx-xx-dem10b-YYYYMMDD.xml` のようなファイルが出てきます。

### 3. Python スクリプトで glb を生成

次のように実行します：

```bash
python3 readGMLandMakeGLB.py FG-GML-*.xml
```

実行が成功すると、`terrain.glb` が生成されます。

### 4. WebAR で表示する

`terrain.glb` と `sample.html` を同じディレクトリに置き、Web サーバーで公開します。

スマートフォンなどで `sample.html` にアクセスし、マーカー（Hiroなど）をカメラに映せば、AR 上に立体地形が表示されます。

## ■ データの出典

国土地理院「基盤地図情報 数値標高モデル」[https://fgd.gsi.go.jp](https://fgd.gsi.go.jp)

---

## ■ ファイル構成

```
GML2GLB/
├── readGMLandMakeGLB.py         # メインスクリプト
├── sample.html                  # A-Frame + AR.js による表示例
└── README.md                    # このファイル
```

---

## 📝 ライセンス

このプロジェクトは MIT ライセンスのもとで公開されています。
