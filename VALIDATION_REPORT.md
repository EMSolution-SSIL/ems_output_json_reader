# EMSolution output.json 検証レポート

検証対象: `C:\EMSolution\build\reader_json_files\results` の JSON 240件。各ファイルの判定と対象項目は `build/corpus_report.json` に記録する。再実行:

```powershell
python tests/run_corpus.py --root ../reader_json_files --report build/corpus_report.json
```

| 判定 | 件数 | 意味 |
| --- | ---: | --- |
| `full` | 221 | 生成された値をすべて時系列として登録 |
| `empty_result` | 18 | キーは存在するが、対応する値が生成されていない |
| `spatial` | 1 | MESHのジオメトリ点に対応する空間値 |
| `incomplete` / `error` | 0 | 想定外の未変換項目／読み込みエラーなし |

`empty_result` には、null の結果群6項目、空配列20項目、`postData: null` の5ファイルが含まれる。項目数とファイル数は異なる。空の項目を時系列として出力せず、元の JSON は `OutputData.raw` に保持する。各ファイルの `unindexed` と `notes` に内訳を残す。

`030_AC/010_ComplexPermeability` の3ファイルで `heatData: null` となるのは、検証計算に使われた EMSolution 2026.09.2 のバグによるもの。ユーザーによると、このバグは当該検証計算後に修正済みである。これらは `empty_result` として記録する。

`050_CoilAnalysis/090_MeshedCOIL/010_Herical` の1ファイルでは、MESHとして定義されたジオメトリデータ267点に対して `forceX`、`forceY`、`forceZ` が出力される。時間ステップ数と一致しないのは正常な仕様である。時系列CSVの対象にはせず、`spatial` として記録し、配列は `OutputData.raw` に保持する。

結論: 240件はすべて正常に読み込めた。想定外の未変換項目はない。値のないキーとMESH空間値の扱いを明示したうえで、本コーパスの検証を終了する。
