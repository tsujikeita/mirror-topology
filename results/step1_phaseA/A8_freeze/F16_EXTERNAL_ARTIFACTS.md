# F16 external artifacts (not stored in git)
The A8a feature stack files exceed GitHub's per-file limit and are kept on the project Drive. They are bound here by SHA256 and were
re-verified byte-for-byte by A8b official (`G_F16_file_sha`, `G_F16_array_sha_local`, both True in `a8b/official/a8b_provenance.json`).

| file (Drive: `mirror_topology/runs_step1_phaseA/a8a_v1.1.2_official/`) | size | file SHA256 | array SHA256 |
|---|---|---|---|
| `s1_Bplus_featurestack_l2_16_N16_common_v1_float64.npy` | 1 001 595 008 B | `aca84c5f39e4b35eccfc01c328874fdef053a09084fe689efa0d4e7b2d0728f1` | `4feac2669642c895e9c1391867b8d0dccd85a0abf3f04fec074ae8ab5af345f6` |
| `s1_Bplus_featurestack_l2_16_N16_common_v1_float32.npy` | 500 797 568 B | `9e433de0742c495068facea43509da1104567ecf9b27c8804c96f86c343ec8a9` | `a0281b4fec848623c14b2bef7d0689da6a07083bcb0d8c553075ef0d2094dd9a` |

Shape (3072, 40755); packing schema `packed_upper_v1` (see `a8a/official/s1_Bplus_featurestack_l2_16_N16_common_v1_manifest.json`,
which also records `iu0`, `iu1`, `basis_lm` and `axis_pixel_ids` hashes). Any consumer must verify both SHAs before use, as A8b does.
