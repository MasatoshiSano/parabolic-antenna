<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-31 | Updated: 2026-05-31 -->

# sim

## Purpose
パラボラアンテナ機構のインタラクティブ 3D シミュレーション群(自己完結 HTML + Three.js CDN、
Python 側にビューワ用の外部依存は足さない方針)。2つの HTML がある:
- `antenna3d.html`: 3軸(Az–El–XEl)回転ジンバルの概念モデル。天頂キーホールと第3軸での除去を実演。
- `tripod3d.html`: 写真の**実機準拠**。中央支点＋3本リニアアクチュエータのパラレル機構で、皿姿勢→脚長と到達円錐を可視化。
いずれも運動学 JS は `pedestal_tilt/` の厳密移植で、起動時に Python 由来 golden と突き合わせる。

## Key Files
| File | Description |
|------|-------------|
| `antenna3d.html` | 3軸(Az–El–XEl)回転ジンバルの概念シム。Three.js r184 を ESM importmap(jsdelivr)で読む単一ファイル。運動学 JS は `three_axis.py` の厳密移植。手動(関節操作)/衛星パス追尾(2軸 vs 3軸)を切替。軌道プリセット＋山頂仰角/方位スライダー＋GEO、3軸の角度 vs 時間グラフ(Az/El/XEl同時)、回転軸の3D描画、XEl中立トグルを備える。起動時に自己テスト(golden値・不変条件・パス総移動量・軌道parity・中立中央・描画整合)を実行しバッジ表示 |
| `tripod3d.html` | **実機準拠**の3本リニアアクチュエータ(パラレル機構)シム。運動学 JS は `actuator_tripod.py` の厳密移植。皿の指向に合わせて3本のアクチュエータが伸縮、脚長 L1/L2/L3 vs 時間グラフ(ストローク帯・超過フラグ)、到達円錐を描画。機構寸法(H/rb/rp/ストローク)はスライダー調整可。起動時に脚長 golden を Python と突き合わせ。 |
| `gen_golden.py` | 両シムの自己テスト golden 値を再生成(`antenna3d.html` 用 `GOLD_FWD`/`GOLD_HOLD`/`GOLD_ORBIT`/パス総移動量/`GOLD_XEL`、`tripod3d.html` 用 `GOLD`=脚長)。`pedestal_tilt/` の数式を変えたら実行して各 HTML に貼り替える |
| `preview*.png` | スクリーンショット(3D＋回転軸 / 3軸時系列 / XEl可動域 / 3本アクチュエータ機構)(README 用) |

## For AI Agents

### Working In This Directory
- **座標規約**: プロジェクトは (N, E, U)、Three.js は (X, Y, Z)=(E, U, N)。単一アダプタ群 `ourWorld`(行列 M、det=+1 の置換回転)の下に全アンテナを配置し、子はすべて (N, E, U) 座標で記述する。これにより各関節の回転を運動学の式どおりに書ける。
- **関節→描画の対応(不変)**: `az.rotation.z=a` (= Rz(a), 軸=Up)、`el.rotation.y=-h` (= Ey(h)=three Ry(−h), 軸=East)、`xel.rotation.z=ξ` (= Rz(ξ))、`mountRoot.setRotationFromAxisAngle((-sinφ,cosφ,0), θ)` (= R_tilt, Rodrigues)。チェーン合成 = `M·R_tilt·Rz(a)·Ey(h)·Rz(ξ)·x̂`。描画される視軸は `forward_3axis` の `u_true` に一致する(起動時の視覚整合テストで検証)。
- 台座傾き θ_t は実寸では1°未満で不可視のため「傾き表示倍率」で誇張描画する。倍率は描画のみに掛け、運動学読み出し(実指向)には掛けない。
- 数式は `pedestal_tilt/three_axis.py` が**単一の真実**。HTML 内 JS はその移植であり、`gen_golden.py` の出力で突き合わせる。`three_axis.py` を変えたら HTML の JS とインライン golden の両方を更新する。
- Three.js は r184 前提の API(`outputColorSpace`/`SRGBColorSpace`、`useLegacyLights` は存在しない、`renderer.setAnimationLoop` / `setDrawRange` による動的ライン)。バージョンを上げる際は importmap の URL と API 差分を確認する。

### Testing Requirements
- ブラウザで `sim/antenna3d.html` を開き、左下バッジが `PASS golden+不変条件+パス(2軸 174.4° vs 3軸 0.0°)+視覚整合` であること。`console.log('[self-test] …')` も確認。
- file:// で直接開ける(ESM は絶対 https の CDN を読むため CORS 問題なし)。ヘッドレス検証は Playwright が file:// を拒否するので `python3 -m http.server` で配信して `http://127.0.0.1:PORT/sim/antenna3d.html` を開く。
- QA でポーズを外部制御する場合は `window.__sim`(状態オブジェクト)を使う。

### Common Patterns
- 円柱メッシュは既定で +Y 方向 → `quaternion.setFromUnitVectors(Vector3(0,1,0), 目標方向)` で向ける。
- 放物面皿は `LatheGeometry`(対称軸 +Y)を `rotation.z=-π/2` で local +x(視軸)へ向ける。
- 動的ライン(天空パス)は最大点数を `Float32Array` で先取りし `setDrawRange` + `needsUpdate`。
- 衛星軌道は `makeOrbit(culmEl, culmAz, geo, n)` が大円(地平→地平, s=-88..88°)または GEO 静止点を生成。プリセットは `ORBITS` 表で `culmEl`/`culmAz`/`geo` を設定するだけ。
- 3軸時系列グラフは別 2D canvas(`#chart`)。`rebuildPass` で `S.ser2`/`S.ser3`(Azはunwrap済み)を前計算し、`drawChart` が3本線＋再生ヘッド＋2軸Azゴーストを描く。色は Az=#ffd34d / El=#ff8a5c / XEl=#4fd1ff(回転軸ロッドと共通)。
- 回転軸ロッドは各 group の局所軸に沿わせ(`axisHelpers`)、`depthTest:false`+`renderOrder=10` で皿の手前に常時描画。表示トグルは `S.showAxes`。
- 第3軸(XEl)可動域は `S.xelMin`/`S.xelMax`(`setXelRange('center'|'edge')`)。中央=[-45,45]・端=[0,90](同90°幅)。グラフに可動域バンドを描き、超過点を赤で強調、読み出し `#rXelFit` に範囲内✓/超過⚠。中立中央なら天頂越えの ±ξ(≈±キーホール半径)が収まる。これは Python の `JointLimits`/`pass_fits_limits` と対応し、自己テストで center可/edge不可を確認。

## Dependencies

### Internal
- 数式の真実は `pedestal_tilt/three_axis.py`。`gen_golden.py` のみ `pedestal_tilt` を import(HTML は import しない)。

### External
- Three.js r184(CDN: jsdelivr, ESM importmap)。それ以外の外部依存なし。

<!-- MANUAL: -->
