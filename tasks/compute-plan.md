# Slice 3 算力清單（2026-10-22，等 Stan 拍板）

來源：scout 讀 villa/spiral-fitting 原始碼＋S3 ListObjects；標 ✅ 的是主 session 親驗過的數字。

## 要跑什麼

```
FIT_SPIRAL_DEVICE=cpu FIT_SPIRAL_CONFIG_OVERRIDES='{"z_begin": 10500, "z_end": 11500, "optimizer_num_training_steps": 10000}'   python fit_spiral.py --dataset ./spiral_datasets/phercparis4
```

- z 視窗只能用 config 的 z_begin / z_end（✅ config.py:401-402，預設 4000..17000），單位 9.6 um voxel。
- 約束檔只認 dataset 根目錄四個固定檔名：abs_winding.json / relative_windings.json / same_windings.json / drawn_control_points.json（✅ fit_session.py:418-423）。
  我們的輸出要合併進 same_windings.json（或替換），不是另給路徑。
  **合併時 collection id 必須重新編號**（verifier 2026-10-22 抓到：我們的 collection id 與人工檔 26 個重疊，
  loader 以檔內 dict key 為 collection id，重疊就蓋掉人工標註；point id 是每個 collection 自己的 dict，
  不同 collection 重疊沒關係，見 point_collection.py:145-171）。做法：offset = 人工最大 collection id + 1。已寫 `merge_pcl.py`，實測人工 154 個 collection（最大 id 174）＋產生的 34 個 → 188 個、id 不重複、人工內容逐 collection 相等（data/out/merged_same_windings_preview.json）。
- 對照設計：同視窗、同 seed、同步數，一組用原 same_windings.json，一組加上版面產生的點集合；比 windaudit／satisfaction 指標與 loss 曲線。

## 要下載（S3 spiral dataset 20261019084150）

| 項目 | 大小 | 必要？ |
|---|---|---|
| umbilicus.json + 三個 winding JSON | 3 MB ✅ | 必要 |
| verified_patches/（實際 22,563 個 tifxyz 目錄，S3 全量列表） | 1.657 GiB ✅ | 必要；fitter 只用 z.tif 篩 z（tifxyz.py:376-399，bbox 不信任、無 margin），所以全抓 |
| winding_inference/ | 0.17 GiB ✅ | 預設 dense_spacing_mode=winding_model 需要 |
| eval_fibers/ | 0.28 GiB ✅ | 可關（input_use_fibers=false） |
| outer_shell/ | 0.01 GiB ✅ | 必要 |
| lasagna_inputs/las_008_nx...respool_g4_pair/ | 9.52 GiB ✅ | normals loss 用；關掉 input_use_normals 就不用（但 fit 品質會變，對照組兩邊同設定即可） |

- 預設設定：約 12 GiB。關 normals：約 2.1 GiB。**G 槽是 Google Drive 掛載，不是本機磁碟**（2026-10-22 資料 agent 發現），資料放 C 槽 `_scratch/2026-10-22-layout-constraints/data/spiral_datasets/`（209 GiB 可用）。
- 不需要 CT 體積本身；tracks（27.7 GiB）、patch_normals（13.9 GiB）、fibers.afv（10.4 GiB）都不用。

## 環境

- Python >= 3.14（✅ pyproject.toml:5；機器上 uv 有 3.14.2），torch >=2.11,<2.13（✅ :32）。
  Windows 下 uv 預設抓 cu128 wheel；CPU 跑要自己裝 CPU wheel 或 `--extra cpu`。
- 四個 nanobind C++ 模組要編（CMake >= 3.22、C++23 編譯器、nanobind）。cmake 本機沒裝。
  CMakeLists 另外要 villa 根目錄的 vc_object_store（✅ cpp/CMakeLists.txt:53，是 CACHE PATH 可改指向），
  目前 sparse checkout 沒拉這個目錄，要補。程式碼有 ImportError fallback，但 fallback 行為沒查。
- 建議用獨立 uv venv，不碰 lab 的 .venv。

## 時間（都是 Apple silicon 數字，x86 沒有任何實測）

- PR #1925：M1 Max CPU、1,000 slices、不含 patches／fibres：1.6 到 2.0 s/step（300 steps 8.7 分）。
- M5 Max MPS 全輸入 0.32 s/step，作者說 MPS 比 CPU 快 2.74x → 推 CPU 約 0.9 s/step。
- 推算：10,000 steps 約 2.5 到 5 小時／一組；30,000 steps 約 7 到 14 小時／一組。對照至少兩組。
- 本機 GTX 1060（Pascal）新 torch CUDA wheel 不支援。租 GPU 的話 1,000 slices 約 1 分鐘／401 steps（headless_fit_driver 註解，較輕設定）。

## 要 Stan 決定的三件事

1. 下載 12 GiB（含 normals）還是 2 GiB（關 normals）。
2. 裝 cmake＋C++ 工具鏈＋uv venv（Python 3.14 + torch CPU wheel），放哪個路徑。
3. CPU 跑（佔機器 5 到 14 小時 × 兩組以上）還是租 GPU（每組幾分鐘）。

未確定：x86 CPU 實際速度；verified_patches 真實總大小；sidecar 能不能只下載視窗那段；spiral_outward_sense 對 PHercParis4 是不是 CW。
