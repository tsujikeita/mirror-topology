# A10 version history（v1.0 → v1.2.9）
| 版 | 日付 | 内容 | 状態 |
|---|---|---|---|
| v1.0 | 2026-09-12 | 初版（中央帯 event・float64 selection・chunk 10000）。サンドボックス official 相当を実行 | superseded（結果撤回） |
| v1.1 | 09-12 | Event B 復元・A8b production path・fail-closed m 判定・2D 較正経路・3 位置 W₂・binding | 未実行（監査で修正） |
| v1.2 | 09-12 | A8b 丸め順・precision policy・Δ_m=log1.10・bootstrap 分子 0・W₂ 独立 stream・安定性 gate | 未実行 |
| v1.2.1 | 09-12 | m ごとの usable・W₂ checkpoint binding・negative control gate・全ペア finite | 未実行 |
| v1.2.2 | 09-12 | scan 非有限 fail-fast・positive control inventory | 未実行 |
| v1.2.3 | 09-12 | 乱数 namespace registry・cross-selection policy（サンドボックスで antipode/非対蹠 flip を発見） | 未実行 |
| v1.2.4 | 09-12 | **ℓ2–4 selection を float64 primary に**・component 別 f32 感度 | 未実行 |
| v1.2.5 | 09-12 | helper 配線修正・W₂ exact-subset bound・chunk binding（実行前監査 PASS） | Colab smoke で healpy 未導入により停止 |
| v1.2.6 | 09-12 | healpy pin・コメント修正 | Colab smoke で quadrature bit-hash gate（NumPy 版依存）により停止 |
| v1.2.7 | 09-12 | quadrature を数学的 gate に | smoke PASS；official で thread gate（複数 BLAS pool）により停止 |
| v1.2.8 | 09-12 | thread gate を NumPy pool 基準に | smoke PASS；**official は最終セルで `G_cal_control_inventory` のみ FALSE（60/61）**：boosted-KDE pdf の underflow。provenance・checkpoints は `history/v1.2.8_official_FAILED/` に保持（console log は取得せず） |
| **v1.2.9** | 09-12 | KDE 密度比を log 空間に | **smoke SMOKE_PASS 54/54・official A10_VALID 61/61**（凍結対象） |
