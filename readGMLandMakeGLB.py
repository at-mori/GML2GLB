# -*- coding: utf-8 -*-

import sys
import os
import numpy as np
import xml.etree.ElementTree as ET
from collections import defaultdict
import trimesh
from trimesh.exchange.gltf import export_glb

# GMLの名前空間
ns = {
    'gml': 'http://www.opengis.net/gml/3.2',
    'fgd': 'http://fgd.gsi.go.jp/spec/2008/FGD_GMLSchema'
}

# GMLファイルから標高データを読み込む関数
def load_dem_from_gml(xml_path):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # グリッドサイズ
        high = root.find('.//gml:high', ns).text.strip().split()
        cols = int(high[0]) + 1
        rows = int(high[1]) + 1

        # 始点座標
        lower_corner = root.find('.//gml:lowerCorner', ns).text.strip().split()
        lat0, lon0 = map(float, lower_corner)

        # tupleListから標高値を取得
        tuple_node = root.find('.//gml:tupleList', ns)
        if tuple_node is None or not tuple_node.text:
            print(f"⚠️ 空のtupleList: {xml_path}")
            return None

        values = []
        for line in tuple_node.text.strip().splitlines():
            parts = line.strip().split(',')
            if len(parts) != 2:
                continue
            _, val = parts
            values.append(float(val) if val != '-9999.00' else np.nan)

        data = np.array(values).reshape((rows, cols))
        # 南北反転（北から入るデータを南からに変更）
        data = np.flipud(data)
        return data, lat0, lon0

    except Exception as e:
        print(f"❌ 読み込みエラー: {xml_path}: {e}")
        return None

def cutout_around_max(grid, size=1000):
    """
    grid内の最大値を中心に、指定サイズの正方領域を切り出す。

    Parameters:
        grid (np.ndarray): 標高データの2次元配列
        size (int): 切り出す正方形の一辺のサイズ（デフォルト1000）

    Returns:
        cutout (np.ndarray): 切り出された2次元配列
        max_value (float): 最大値
        center_row (int): 最大値の行インデックス
        center_col (int): 最大値の列インデックス
    """
    # NaNを無視して最大値の位置を取得
    flat_index = np.nanargmax(grid)
    center_row, center_col = np.unravel_index(flat_index, grid.shape)
    max_value = grid[center_row, center_col]

    half = size // 2

    # 範囲を制限（gridの端を越えないように。中心を合わせるように奇数のグリッドに。）
    start_row = max(center_row - half, 0)
    end_row   = min(center_row + half+1, grid.shape[0])
    start_col = max(center_col - half, 0)
    end_col   = min(center_col + half+1, grid.shape[1])

    cutout = grid[start_row:end_row, start_col:end_col]

    print(f"✅ 最大値: {max_value}, 位置: row={center_row}, col={center_col}")
    print(f"✅ 切り出しサイズ: {cutout.shape}")    

    return cutout, max_value, center_row, center_col

def concat_data(files):
    tiles = []

    for f in files:
        if not os.path.exists(f):
            print(f"⚠️ ファイルが見つかりません: {f}")
            continue
        result = load_dem_from_gml(f)
        if result:
            data, lat0, lon0 = result
            print(f"✅ 読み込み成功: {f}, shape={data.shape}, lat0={lat0}, lon0={lon0}")
            tiles.append((data, lat0, lon0))

    if not tiles:
        print("⚠️ 有効な標高データが1つも読み込めませんでした。")
        sys.exit(1)

    # 緯度 → 経度 の順にソート
    tiles.sort(key=lambda t: (t[1], t[2]))

    # 緯度帯ごとに経度順で並べて横方向に連結
    rows_by_lat = defaultdict(list)
    for data, lat0, lon0 in tiles:
        rows_by_lat[lat0].append((lon0, data))

    rows = []
    for lat0 in sorted(rows_by_lat.keys()):
        row_tiles = sorted(rows_by_lat[lat0], key=lambda x: x[0])  # 経度でソート
        row_data = [tile for _, tile in row_tiles]
        row = np.hstack(row_data)
        rows.append(row)

    # 最終的な全体グリッドを縦方向に連結
    grid = np.vstack(rows)
    print(f"✅ 完成グリッドサイズ: {grid.shape}")

    return grid

def downsample_with_center(cutout: np.ndarray, step: int) -> np.ndarray:
    """
    中心を含み、n個飛びに間引いた配列を返す。

    Parameters:
        cutout: 元の2D numpy配列（奇数サイズ想定）
        step: 間引き間隔（例: 2なら1つおき）

    Returns:
        新しい間引き済み配列
    """
    # サイズを奇数に調整
    if cutout.shape[0] % 2 == 0:
        cutout = cutout[:-1, :]
    if cutout.shape[1] % 2 == 0:
        cutout = cutout[:, :-1]

    # 修正後のサイズを取得してからアサート
    h, w = cutout.shape
    assert h % 2 == 1 and w % 2 == 1, "cutout のサイズは奇数である必要があります"

    center_i = h // 2
    center_j = w // 2

    i_start = center_i % step
    j_start = center_j % step

    return cutout[i_start::step, j_start::step]

def generate_triangle_mesh(Z: np.ndarray, scale=10):
    """
    標高データ Z から三角形メッシュ用の vertices と faces を生成。

    Parameters:
        Z: 2D numpy array（標高データ）
        scale: X,Y方向のスケーリング係数（1単位=1mなど）

    Returns:
        vertices: (N, 3) numpy array
        faces: (M, 3) numpy array（頂点のインデックス3つずつ）
    """
    h, w = Z.shape
    x = np.arange(w) * scale
    y = np.arange(h) * scale
    xv, yv = np.meshgrid(x, y)

    # 頂点リスト生成
    vertices = np.stack([xv.ravel(), yv.ravel(), Z.ravel()], axis=1)

    # 三角形リスト生成
    faces = []
    for i in range(h - 1):
        for j in range(w - 1):
            idx = i * w + j
            # 三角形1
            faces.append([idx, idx + w, idx + w + 1])
            # 三角形2
            faces.append([idx, idx + w + 1, idx + 1])
    faces = np.array(faces, dtype=np.int32)

    return vertices, faces

def export_mesh_to_glb(vertices: np.ndarray, faces: np.ndarray, color=(0, 255, 0), filename: str = "terrain.glb"):
    """
    三角形メッシュ（vertices と faces）から glb ファイルを生成して保存。
    NaN を含む三角形は除外することで、透明（穴あき）表現を実現。

    Parameters:
        vertices: 頂点座標の配列（N×3）
        faces: 三角形インデックス配列（M×3）
        filename: 出力ファイル名（.glb）
    """
    # 面の向きを修正（flipud 後の配列に対応）
    corrected_faces = faces[:, ::-1]

    # NaNを含む三角形を除外
    z = vertices[:, 2]
    valid_faces = [tri for tri in corrected_faces if not np.isnan(z[tri]).any()]
    valid_faces = np.array(valid_faces)

    print(f"✅ NaNを含まない三角形数: {len(valid_faces)} / {len(faces)}")

    # メッシュ作成
    mesh = trimesh.Trimesh(vertices=vertices, faces=valid_faces, process=False)

    # RGBAカラー設定
    rgba = np.array([[*color, 255]] * len(vertices), dtype=np.uint8)
    mesh.visual.vertex_colors = rgba

    # シーンに追加
    scene = trimesh.Scene(mesh)

    with open(filename, 'wb') as f:
        f.write(export_glb(scene))
    print(f"✅ glbファイルを出力しました: {filename}")

def main():
    if len(sys.argv) < 2:
        print("使い方: python3 readGML.py ファイル1.xml ファイル2.xml ...")
        sys.exit(1)

    # ファイルを読み込み、tiles データを作成する。
    grid = concat_data(sys.argv[1:])

    # 切り出し
    cutout, max_val, row, col = cutout_around_max(grid, 500)

    # 海を表示できるように。
    cutout = np.nan_to_num(cutout, nan=0.0)
    
    # 間引き。中心は保持したままで。
    cutout = downsample_with_center(cutout, 3)
    
    vertices, faces = generate_triangle_mesh(cutout,20)
    # ----- 平行移動でモデル原点を中心に -----
    vertices[:, 0] -= (np.max(vertices[:, 0]) + np.min(vertices[:, 0])) / 2
    vertices[:, 1] -= (np.max(vertices[:, 1]) + np.min(vertices[:, 1])) / 2

    # ----- 高さの最小値を引いて 0 に揃え -----
    vertices[:, 2] -= np.min(vertices[:, 2])

    # --- 高さの最小値をゼロに揃える ---
    # min_z = np.nanmin(vertices[:, 2])
    min_z = np.nanmin(cutout)
    vertices[:, 2] -= min_z  # Z方向（高さ）を底上げ

    # --- Z-up → Y-up 変換（AR.js 用） ---
    vertices = vertices[:, [0, 2, 1]]  # X, Z, Y に並べ替え
    vertices[:, 2] *= -1              # Y軸（旧Z）を反転
    
    export_mesh_to_glb(vertices, faces)
    
if __name__ == "__main__":
    main()
