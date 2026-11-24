# emso-post

[English README](README.md) · [今後の予定](ROADMAP.md)

EMSolution の `output.json` に含まれるポストデータを CSV に出力し、独立した画面で二次元グラフを表示する Python ツールです。現時点では `convergence_history.json` と `mesh_info.json` は対象外です。

## インストール

Python 3.10 以降を用意し、このフォルダで次を実行します。

```powershell
python -m pip install -e ".[plot]"
```

CSV 出力だけを使う場合は `python -m pip install -e .` で構いません。別のプロジェクトから使う場合は、このフォルダへのパスを指定してインストールします。[GitHub Releases](https://github.com/EMSolution-SSIL/ems_output_json_reader/releases) の wheel もインストールできます。インストール後は `emso-post` コマンド、または `python -m emso_post` を利用できます。

## CSV とグラフ

```powershell
emso-post run C:\path\to\output.json --config selection.yaml --out C:\path\to\results
emso-post run C:\path\to\output.json --out C:\path\to\results
emso-post export C:\path\to\output.json --out C:\path\to\results
emso-post plot C:\path\to\output.json
```

- `run`: CSV を出力してからグラフ画面を開きます。
- `export`: 画面を開かずに CSV だけを出力します。
- `plot`: 元の JSON にある全系列から選ぶグラフ画面を開きます。
- `--config` を省略すると、JSON に存在する出力可能な時系列をすべて CSV に出します。グラフ画面の候補は `--config` で制限されません。
- `--out` を省略すると、入力 JSON と同じ場所の `post_csv` ディレクトリに出力します。既存 CSV は保護されます。上書きする場合は `--overwrite` を指定します。
- 入力には `output.json` 自体、またはその格納ディレクトリを指定できます。

CSV は `postData` のデータ群ごとに作成されます。たとえば `forceNodal_forceNodalData.csv` です。先頭に `stepNo`、`time`、利用可能なら位置や電気角を置き、その後に ID・項目・単位を含む列を配置します。`binteg` の計算点座標は `binteg_points.csv` に出力します。文字コードは Excel で読みやすい UTF-8 BOM 付きです。

## YAML での選択

```yaml
exports:
  - post: forceNodal
    group: forceNodalData
    ids: [rotor, 10]
    fields: [forceMZ, forceX]
  - post: network
    group: networkData
    ids: [1, 2, 3]
    fields: [current, voltage, flux]
```

`post` は必須です。`group`、`ids`、`fields` を省略すると、その範囲内のすべてを選びます。ID は JSON と同じ型で指定します。`coilForce` のような複合 ID は `ids: [{seriesNum: 1, divisionNum: 2}]` の形式です。存在しない種別・ID・項目を指定するとエラーにします。実行例は [examples/selection.yaml](examples/selection.yaml) にもあります。

## グラフ画面

画面でポストデータ種別、データ群、ID、項目を選びます。ID と項目は複数選択でき、先頭の値をプレビューできます。横軸は時刻を初期値とし、存在する場合は位置や電気角も選べます。異なる単位の系列は別々の縦軸に表示します。静解析など 1 点の結果は点で表示します。

グラフ機能には Matplotlib と Tkinter が必要です。Tkinter は通常の Windows 向け Python に含まれますが、環境にない場合は Python 側で追加してください。

## Python から使う

```python
from emso_post import load_output, load_selection, select_series, export_csv

output = load_output(r"C:\path\to\output.json")
for series in output.series:
    print(series.post, series.group, series.id_label, series.field, series.unit)

selection = load_selection("selection.yaml")
chosen = select_series(output, selection)
paths = export_csv(output, "results", selection)
```

`output.raw` には読み込んだ JSON 全体、`output.axes` には利用可能な横軸が残ります。`output.series` は元の配列を参照するため、通常のデータ群で値を複製しません。

## 対応範囲と検証

現行の EMSolution 生成コード `src/post/post_files/EMSOJson.cpp` にある `output.json` の14種類のポストデータを対象にしています。`../reader_json_files/results` の実データ240件はすべて読み込めました。221件は全値を時系列として登録でき、18件はキーがあっても値が生成されておらず、1件は正常なMESHの空間値です。2026.09.2のComplexPermeabilityの既知バグとMESHのジオメトリ点の値もレポートに記録しました。時系列に登録しない項目の位置は `output.unindexed` に記録し、元の値は `output.raw` に保持します。詳細は[検証レポート](VALIDATION_REPORT.md)を参照してください。同じ ID が複数ある場合は `recordNo` で区別し、YAML では元の ID でまとめて選択できます。`network.convertedData`、`forceNodal.forceNodalExtendData`、`heat.sourceHeatData` も対象です。

未知のポストデータ、未対応のデータ群、時系列の長さの不一致があれば、黙って欠落させずエラーにします。新しい EMSolution 出力形式に対応する際は、まず `emso_post/core.py` の定義とテストを更新してください。

テスト実行:

```powershell
python -m unittest discover -s tests -v
python tests/run_corpus.py --root ../reader_json_files --report build/corpus_report.json
```

コーパス用スクリプトは各ファイルの判定を JSON レポートに保存します。終了コードは全件読み込め、時系列に登録しない値が「出力なし」または正常なMESHの空間値と分類できた場合に0、読み込み・解析エラーがあれば1、分類できない値が残れば2です。後者を許容する場合は `--allow-incomplete` を指定できます。実データはパッケージに含めません。

従来の `read_emsojson_motor.py` と `dq_trans.py` はモータ固有の試作スクリプトとして残しています。汎用 CLI はこれらを実行しません。
