# WebAR Terrain Model Generator

このプロジェクトは、国土地理院の GML 形式の標高データ（10m メッシュ）を読み込み、指定領域を切り出して 3D 地形モデル（glb形式）としてエクスポートする Python スクリプトです。AR.js + A-Frame を使ったマーカーベースのWebAR表示を目的としていますので、HTML ファイルの例も提供します。

## 🔧 必要な環境

- Python 3.8 以上
- 利用するモジュール  
sys, os, numpy, xml, collectins, trimesh

### インストール手順

```bash
git clone https://github.com/at-mori/GML2GLB.git
cd GML2GLB
