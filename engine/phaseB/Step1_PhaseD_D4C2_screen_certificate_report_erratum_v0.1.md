# Erratum v0.1 to `D4C2_screen_certificate_report.md`（2026-10-08；原本は byte 保持；本 erratum は別文書）

対象：登録原本 `registered_assets/d4c2/results/D4C2_screen_certificate_report.md`（SHA-256 `b9a96cecd1cd6b9d27030381198512d4f05525a8451cb2d4e2d4125b7d179d02`）の **§5 (iii) の括弧書き**：

> 「W₂ unknown の size が各 family にある限り global 較正は usable に到達できない，という固定分母の代数的事実」

監査 `D4C2_screen_certificate_0.112.0_acceptance.json`（`interpretation_correction`：NONBLOCKING_EXPLANATORY_ERRATUM_REQUIRED_FOR_NO_GO_TEXT）および監査報告 §5.2 のとおり，この省略は**強すぎる**。W₂ unknown の存在だけでは，event-ratio trigger の True によって全 size を 12 位置化し未決を解消する経路を排除できない。

## 訂正後の記述
今回の成功不能（usable == True の到達不能）が成立したのは，次の **3 条件の組合せ**による：
1. 各 family（E2／E7／E8）に，登録 D-2W W₂ 判定が **unknown の size が少なくとも 1 つあり，True の size がない**こと；
2. 登録 pseudo **全 2000 行**・全 surviving size・3 position・**N0／N4 両 prefix** で，matched system の exact hit count がすべて正で，**6 つの hit rate の包絡比（max／min）が 2.0 以下**であること（screen の count-envelope 条件；実測最大 1.159）；
3. 固定された位置拡張（event-ratio trigger＝max／min > 2.0）・eligible／TECH 集約規則（technical_fail ＞ True ＞ unknown ＞ False；同一 global row は 1 回のみ計数；分母 2000 固定；閾値 support 0.05／strong 0.01）。

この 3 条件の下で，各 screened family-row の eligible truth は **unknown（required 計算に技術失敗があれば technical_fail）** となり，非技術的に完了すれば c＋u＝2000，Wilson 上限＝1 で両閾値を超える；技術失敗を含む完了でも usable＝True は得られない。E2／E7／E8 の**いずれか 1 family の証拠だけでも 2000 global 行を覆う**（3 family は同じ行の補強証拠であり，6000 試行の較正ではない）。E1 を False と仮定する必要はなく，E1 の結果が何であれ元の any-family 可用性基準を救えない。

## 何の no-go ではないか（監査 §5.3）
固定した Monte Carlo 資産・観測者位置の判定規則・2000 組の等方擬似観測・0.112.0 の登録判定 semantics に**条件付けた較正可用性の成功不能証明**である。Theme T の物理的問い（観測 Event B の裾確率をトポロジー模型が等方模型より改善するか）に対する否定証明ではない；target を評価しておらず，観測での Q／logD・模型の supported／unsupported・トポロジーによる説明不能は示していない；すべての将来 pseudo 集合・別 bank・別 W₂ 手続・強制 12 位置 fallback・別統計量に一般化しない；真の false-support 率が 100% であるとの推定でもない。正式 global 較正の完了・実測 c／u／率・正式 usable＝False・Phase E／実観測 target の解放は含まれない。

## 論文向けの記述（監査 §5.3 の案を採用）
> 本研究で固定した Monte Carlo 資産，観測者位置の判定規則および 2,000 組の等方擬似観測に対し，E2・E7・E8 の全行で，3 位置と N0／Nmax 両 prefix にわたる正の事象確率の包絡比が 2 以下であることを確認した。各 family に登録済み W₂ 未決 case が存在し，W₂ による拡張の確定 True がないことと合わせ，各行は既定の適格性判定では unknown，または required 計算失敗時には technical_fail となる。したがって固定分母による保守的な any-family 較正は support／strong のいずれでも usable＝True へ到達できないことを，全行の Q／KDE 評価を完走することなく証明した。この結果は当該登録手続の較正可用性に関する成功不能証明であり，宇宙のトポロジー一般や観測異常のトポロジー起源を否定するものではない。
