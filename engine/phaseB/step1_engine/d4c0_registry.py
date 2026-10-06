# -*- coding: utf-8 -*-
"""D4C-0 registration (registered_assets/d4c0): the accepted FORMAL pseudo column generation (D4C-0b; attempt 20261004T102334Z_6e681d78a0; commit 12980202, engine 0.103.0)
and the accepted FORMAL D-2W nine-case W2 run (D4C-0a; attempt 20261004T144349Z_cb8bc8e5f7; commit f3aec793, engine 0.104.0), each registered as its ORIGINAL bytes (inner
archive AND extracted members, executed notebook, the ChatGPT acceptance documents) and each bound to ITS OWN historical execution lock (the two runs have different execution
commits; neither lock is rewritten to the registration version). The failed D-2W attempt 20261004T102439Z_9bac8f8730 (commit 12980202; stopped at input resolution, no W2
evaluated) is kept SEPARATELY as failure history (its archive + 6 records) and is never a success source.
Every identity below is a module CONSTANT copied from the accepted originals and from the two acceptance documents (D4C0_pseudo_12980202_acceptance.json 08efa1d1...,
D4C0_D2W_f3aec793_acceptance.json c9506e0b...): file SHA / bytes of every registered member, execution locks, column / paired identities and NPZ identity of the pseudo
columns, the canonical nine case keys with their manifest / result SHAs and exact decisions, the context SHA. build_d4c0_ledger(root, ctx) is a DETERMINISTIC re-derivation
that re-reads every original and refuses any inconsistency (archive members == registered files, lock / final / run records bound to the constants, acceptance documents' file
maps == the registered members, NPZ re-verified with verify_pseudo_columns against the CONSTANT identity, case records bound to the run summary); verify_* requires equality
with the re-derivation; load_registered_d4c0_ledger binds the committed ledger to the d3 pins (d4c0_ledger_sha256) AND requires the pins to carry both acceptance identities,
the context SHA and the pseudo column identities (wrong / missing / null refused).
CONSUMER LOADERS (the bodies behind w2_cases.load_registered_w2_context and d4_pseudo.load_registered_pseudo_columns): load_registered_w2_context authenticates the full
case / run / context / lock document bytes (ledger == constants == pins), then RESTORES the typed W2Context through the existing restore_w2_context with expected_context_sha256
taken from the AUTHENTICATED PINS (never from the editable record), require_formal=True, the canonical nine keys, and requires every re-issued decision to equal the registered
constant decision (the four w2-unresolved cases stay unknown; nothing is promoted). load_registered_pseudo_columns authenticates the original NPZ bytes and re-verifies the
columns against the CONSTANT identity (n = 2000, m = 1, dtypes, ordered paired rows, UIDs, column / paired SHAs) - a cross-environment regeneration or tolerance-equivalent is
never accepted. Nothing here evaluates calibration, thresholds, labels or noise."""
from __future__ import annotations
import copy, hashlib, json, os, zipfile
from typing import Dict, Optional, Tuple
from .errors import InputContractError
from .d3_profile import TwelveContext, _require_ctx
from .official_gate import recorded_environment_registered

LEDGER_SCHEMA = "d4c0_registration_ledger_v1"; RECEIPT_SCHEMA = "d4c0_outer_receipt_v1"
CANON_CASES = tuple(f"{f}/{s}" for f in ("E2", "E7", "E8") for s in ("L1.00", "L1.20", "L1.50"))
PSEUDO_REQUIRED = ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_phaseC_members", "G_env_lock", "G_external_loader_sha", "G_pseudo_table", "G_generated", "G_columns_verified", "G_record_saved")
D2W_REQUIRED = ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_phaseC_members", "G_env_lock", "G_external_loader_sha", "G_twelve_context", "G_shared_null", "G_d2_inputs_resolved", "G_cases_assembled", "G_context_built", "G_records_restored", "G_record_saved")

PSEUDO = dict(
    attempt="20261004T102334Z_6e681d78a0", registered_dir="pseudo/runs/20261004T102334Z_6e681d78a0",
    execution_lock=dict(commit="12980202ee111a26c0a608e7e5bba6caed5302ae", engine_version="0.103.0", inventory_sha256="f04e739d79bb950ff906c341d504c2d30cb8f6c3ad40ad5d3f9f11ff10446429", script_sha256="a6e0772ae62c1a41d0592031276547592830418b47e50ae156aaf180f381d267", table_file_sha256="31fc50c310be59ba82ad9236408174fe3be8db291adf1cfcb96bbc961374d44c", table_sha256="88f5659e1cc373b051f2786d151e474af3bd689e1a21474d0d4da3f6579d3c31", pins_sha256="a3d90b81745bd877922d750d270167478b28614bd593a29f6cf8382c5119d8c7", lock_file_sha256="4b31d9efa65d8cbde62ebd1a081eaf9a71b9426cd70595bab940e5f3ba7a4773", locked_utc="2026-10-04T10:23:34Z"),
    archive=dict(file="d4_pseudo_12980202ee11.zip", sha256="57c0df458eb013c0450b57d880fdf837dcdb1f8f902a6b8b6350e1fa2d43b826", bytes=50138),
    files={"d4_pseudo_final_record.json": {"bytes": 5151, "sha256": "3ff48294bff600dab41168b04a6e61396918bffd90f3d1e0e166090b389f16ea"}, "d4_pseudo_lock.json": {"bytes": 929, "sha256": "4b31d9efa65d8cbde62ebd1a081eaf9a71b9426cd70595bab940e5f3ba7a4773"}, "d4_pseudo_stderr_20261004T102334Z_6e681d78a0.txt": {"bytes": 0, "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}, "d4_pseudo_stdout_20261004T102334Z_6e681d78a0.txt": {"bytes": 349, "sha256": "f65e5d245adcf1d6bf7833c12e6b8f20cfef904f9bb0126e6c77eb9ff7843aeb"}, "run_20261004T102334Z_6e681d78a0/d4_pseudo_columns.npz": {"bytes": 145444, "sha256": "c62a965b3b649870977d95ba247bf84a9580131109fc8572971e06b98da490f2"}, "run_20261004T102334Z_6e681d78a0/d4_pseudo_record.json": {"bytes": 6277, "sha256": "ad4fda8d3d25f684ed5ee1993b12d95e647fd741263c1b669903b0507abfe2d1"}, "run_20261004T102334Z_6e681d78a0/d4_pseudo_stdout.log": {"bytes": 292, "sha256": "ad9031a67290593690594a619e665593a878f959426c1bbc1a771865c8c0b3eb"}},
    executed_notebook=dict(file="MirrorTopology_Step1_D4_pseudo_v0_1_executed_12980202ee11.ipynb", sha256="fb7a0d663694eac623a169006d9f0ac21c8a382213655ad357d9fbf938add973", bytes=29797),
    acceptance=dict(file="D4C0_pseudo_12980202_acceptance.json", sha256="08efa1d19b29303425125aed71f96f0f27765c03234b36164f98ba4631cbee5b", bytes=12330, decision="PASS_WITH_EXPLICIT_SCOPE__PSEUDO_ORIGINAL_COLUMNS_ACCEPTED_FOR_REGISTRATION"),
    supplementary=dict(audit_md=dict(file="ChatGPT_audit_D4C0_runs_12980202_and_v3_0.104.0.md", sha256="21abf2d5dd4e20ba1b660b89ac856a03938cf8cfefc3fdec57474bd98ffd692a", bytes=13483), v3_decision=dict(file="D4C0_v3_0.104.0_audit_decision.json", sha256="c54673b5b265cf03029ceb0504ec9d35d92f7e662a314b7a04264a49fcf4cb80", bytes=9489)),
    columns={"AX_sha256": "60d61625987b85fac70befb1ad7a0f89c829b37e115cbccff6613c478616ddc7", "PL_sha256": "85a035007b2f831c9d4d84a8a9ad70264d5a9300f54d59d23b1f2a03ede343c3", "T1_sha256": "6e2669b529440d94a3808061788e3c0100b374075f319127914d4f7725af091d", "T2_sha256": "1a5588fd8dc3efb6cca7beaf446a3a88ffb9d3ff0b2835a2cf07751f4c3ee3d3", "cid_sha256": "55f385cf2332d9056aaed6f496e7bebd2df52c6a9547ce2144b309432d4b0290", "dtype": {"AX": "int32", "PL": "int32", "T1": "float64", "T2": "float64", "cid": "int64"}, "first_uid": [1, 400, 5001, 0, 0], "last_uid": [1, 400, 5001, 0, 1999], "m": 1, "n": 2000, "paired_sha256": "c9f75cdb86c90b0c73409a3e7a015faaef1e5903788358082dde3c21d66a1d15", "uids_sha256": "cb90d89c16d8d06acc52c7aa5b043eae36c489d23d08037a3652e3ff56bf11ea"},
    npz={"bytes": 145444, "file": "d4_pseudo_columns.npz", "sha256": "c62a965b3b649870977d95ba247bf84a9580131109fc8572971e06b98da490f2"}, root_sha256="390dbfaca62d4d891b69b6a54906cd4d5f6724a0b6a170e1ef3bd69f15ef7c4c", rng_keys=dict(rotation=[20260912, 1, 400, 5001, 0, 1], gaussian=[20260912, 1, 400, 5001, 0, 0]))
D2W = dict(
    attempt="20261004T144349Z_cb8bc8e5f7", registered_dir="d2w/runs/20261004T144349Z_cb8bc8e5f7",
    execution_lock=dict(commit="f3aec79358452a293ccced14efd4f7e3ad240477", engine_version="0.104.0", inventory_sha256="49976b3e24e27ee614c8e31bb2b292554cf550b95a189c96e9cd190fc92df6f2", script_sha256="dcd64283d87ef0e0b14a68fc0e8a889743db4f66ae6ee0bd0881652bf4ead8e6", ledger_file_sha256="07574dfa58dcabdf42955b8cc90cd7adf8fa581ae8075587e540c68f07263555", asset_file_sha256="cc67686744f513e3123de2fb8353d79491d4b1deaff2b8d9ecb5f93d0f95afb4", pins_sha256="de1794b592c16c9327055af4a926d001106589124c7d5fe3647247c2b3a0a78b", lock_file_sha256="9f01508a898f11440e146633e4b95395db4b8471f5a7d184a2e9bec9c0c2f720", locked_utc="2026-10-04T14:43:49Z", d2_run_roots={"E2": "/content/drive/MyDrive/MirrorTopology_D2/E2_20260923T092030Z/out/d2", "E7": "/content/drive/MyDrive/MirrorTopology_D2/E7_20260923T125656Z/out/d2", "E8": "/content/drive/MyDrive/MirrorTopology_D2/E8_20260923T174910Z/out/d2"}),
    archive=dict(file="d2w_cases_f3aec7935845.zip", sha256="13e222e57d624473eba4fda045d400b34bf9a3fda6623fe74eacb1325a53a72b", bytes=5646698),
    files={"d2w_final_record.json": {"bytes": 6184, "sha256": "c29fc6c6be7e6ee614e67e93743b35d60f37a8a94c532671fb8d0eb37b6de01a"}, "d2w_lock.json": {"bytes": 1219, "sha256": "9f01508a898f11440e146633e4b95395db4b8471f5a7d184a2e9bec9c0c2f720"}, "d2w_stderr_20261004T144349Z_cb8bc8e5f7.txt": {"bytes": 0, "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}, "d2w_stdout_20261004T144349Z_cb8bc8e5f7.txt": {"bytes": 1212, "sha256": "c452d944fb5b01c576c834202671b9ec1d200d6d01f27de4e4490107456ce9c8"}, "run_20261004T144349Z_cb8bc8e5f7/cases/d2w_case_E2_L1.00.json": {"bytes": 3857374, "sha256": "373dd745a20d0abfbce58dfc89f956a744b92dd66439301c6cb56a4a24856e28"}, "run_20261004T144349Z_cb8bc8e5f7/cases/d2w_case_E2_L1.20.json": {"bytes": 3859841, "sha256": "fbae69d4a3e6c0a8d22e8cb3459e947e1f3c701dcc00cc352b862a3c28530a2a"}, "run_20261004T144349Z_cb8bc8e5f7/cases/d2w_case_E2_L1.50.json": {"bytes": 3857414, "sha256": "9a4ca36b32bcb508751203c75f93e192e931408ab5d54364bc13e29b61961087"}, "run_20261004T144349Z_cb8bc8e5f7/cases/d2w_case_E7_L1.00.json": {"bytes": 3857394, "sha256": "383a5f60576782297db46c53e56ca78447ac067c128d682bbeda8deed9fb1367"}, "run_20261004T144349Z_cb8bc8e5f7/cases/d2w_case_E7_L1.20.json": {"bytes": 3858506, "sha256": "72d3c5b9d6e33a42d9b9ba5f36c933863a9a540155121d157b2b249d1821f63f"}, "run_20261004T144349Z_cb8bc8e5f7/cases/d2w_case_E7_L1.50.json": {"bytes": 3857346, "sha256": "c94fc2f0ddb56ccec853763fd3cd06fdf3aa185bfe27e793c5231844fc065e2f"}, "run_20261004T144349Z_cb8bc8e5f7/cases/d2w_case_E8_L1.00.json": {"bytes": 3857267, "sha256": "860614e5a8f91123e514b946fccb99927c6d05d38b362adab3bf047ed52681ed"}, "run_20261004T144349Z_cb8bc8e5f7/cases/d2w_case_E8_L1.20.json": {"bytes": 3857353, "sha256": "0351be84ae5c17475c060b88ff7332de0dbd4d8912fb2dcefecf8e838e8e7062"}, "run_20261004T144349Z_cb8bc8e5f7/cases/d2w_case_E8_L1.50.json": {"bytes": 3857449, "sha256": "4a5590bc25b70c9a8c9827da94c15f48fd1a417c4a591d30b3f04d6239f693ca"}, "run_20261004T144349Z_cb8bc8e5f7/d2w_context_record.json": {"bytes": 8707, "sha256": "58406d1b432611823fe8b3ac47b66d8c28186b007095c74d00bf6815dea603ed"}, "run_20261004T144349Z_cb8bc8e5f7/d2w_run_record.json": {"bytes": 16757, "sha256": "5438e14918aa60f9d88121743112b3eec7b2c3a0391877c82e323b92980fbf6d"}, "run_20261004T144349Z_cb8bc8e5f7/d2w_stdout.log": {"bytes": 1161, "sha256": "d229b0c47f4f6adc554015d262e224814ce97c7f3988b4e4b5e8a6b525405e93"}},
    executed_notebook=dict(file="MirrorTopology_Step1_D2W_cases_v0_1_executed_f3aec7935845.ipynb", sha256="3d8a7ff7519e971b8981ff73256c2d975c8a7bc8ab11b7cc876c98a55807e89c", bytes=38708),
    acceptance=dict(file="D4C0_D2W_f3aec793_acceptance.json", sha256="c9506e0b17f7ef17c3d1168e0acabdbba0195748060ca531b8c22305dbbd922a", bytes=78367, decision="PASS_WITH_EXPLICIT_SCOPE__D2W_FORMAL_RUN_ACCEPTED__REGISTRATION_DRAFTING_AND_TESTS_GO"),
    audit_md=dict(file="ChatGPT_audit_D2W_run_f3aec793.md", sha256="bc522141fd2b80a7a280dffd472a6d783516d5824b4e443781e22837e7cdf9db", bytes=14890),
    context_sha256="50ec5a54d593d9bc53ce3661292d7dd3cb385369511a3444fda62226e77acb9c", asset_sha256="8348d5f4733ae5a37e39f4aa88109626e5caab312b55bd108be7ec9e5daff3ba",
    cases={"E2/L1.00": {"B_final": 400, "file": "d2w_case_E2_L1.00.json", "file_bytes": 3857374, "file_sha256": "373dd745a20d0abfbce58dfc89f956a744b92dd66439301c6cb56a4a24856e28", "manifest_sha256": "12ae8b72cdb4d85300e31a5e2f78c0c7b52c12d87c50d7e075c7d3eecbca159b", "observed_hash": "1f1f502d2d62ba9a70ea185c2c3e35d8b0a2af5137b6367eb9ac0c2b65430809", "result_sha256": "78a866b51877f80ab8d86c0f432cc2fd1fd0e150c95879e4328ba636d5ee67d2", "trigger": False, "validation_state": "valid"}, "E2/L1.20": {"B_final": 800, "file": "d2w_case_E2_L1.20.json", "file_bytes": 3859841, "file_sha256": "fbae69d4a3e6c0a8d22e8cb3459e947e1f3c701dcc00cc352b862a3c28530a2a", "manifest_sha256": "fe72cb9b0a105acd190d1e7e2b3b5950335d6c87419fae5ffbee7947e0c8bcbd", "observed_hash": "bedf37dd9ad32f98a6da4d47f281a9ce7ea5e463e74d36fcacfe4d29320a059c", "result_sha256": "b03edae90fd17cf2559d5bd5d7cf8b685d9940e6f203533bb6d1c9f7e02345ee", "trigger": "unknown", "validation_state": "w2-unresolved"}, "E2/L1.50": {"B_final": 400, "file": "d2w_case_E2_L1.50.json", "file_bytes": 3857414, "file_sha256": "9a4ca36b32bcb508751203c75f93e192e931408ab5d54364bc13e29b61961087", "manifest_sha256": "a6f93d886de53e43c514ab812c633a5df5c44bbc65c5ef3c7ee567153fa68a8b", "observed_hash": "bb7e073f26e0655656d1a74348226cbd4edc329e52c3cb2ebd218a9f1fd7417b", "result_sha256": "578cf562c4fc306b0c3a102c841d480d6e6f4250f7a3ba07d5d129dd139229a0", "trigger": False, "validation_state": "valid"}, "E7/L1.00": {"B_final": 400, "file": "d2w_case_E7_L1.00.json", "file_bytes": 3857394, "file_sha256": "383a5f60576782297db46c53e56ca78447ac067c128d682bbeda8deed9fb1367", "manifest_sha256": "b5db1f77b6397c876c32d7847dd85783774aff06116c580d90a76dcc9476c940", "observed_hash": "66ff2fe996740764bc4f29aa0806abf6a2185a12ed955703fba681d279741a93", "result_sha256": "d12a92d1461a45fc89007208855584f553f16ebc60538ba4e17d678871754e3e", "trigger": False, "validation_state": "valid"}, "E7/L1.20": {"B_final": 600, "file": "d2w_case_E7_L1.20.json", "file_bytes": 3858506, "file_sha256": "72d3c5b9d6e33a42d9b9ba5f36c933863a9a540155121d157b2b249d1821f63f", "manifest_sha256": "47540dd18fb026819300ff2ddf75d89101d924e878dec3fabf47bc1205e1a2d4", "observed_hash": "a42e48477e642e2cfb011019501a5cdcfa5b5ac69ee5145bf948d1b325a22b9a", "result_sha256": "3e0e5aa12096eafcdc20298edae9fc1e45cc633f106da032ff9981516859a5ce", "trigger": "unknown", "validation_state": "w2-unresolved"}, "E7/L1.50": {"B_final": 400, "file": "d2w_case_E7_L1.50.json", "file_bytes": 3857346, "file_sha256": "c94fc2f0ddb56ccec853763fd3cd06fdf3aa185bfe27e793c5231844fc065e2f", "manifest_sha256": "01288193855f67b64e429fbd5ac1fb4d09977e2add4459e1f471f95d9c20b740", "observed_hash": "c93d9aa865f2b342c631f089ce780bcbc4318e71439365d4af65b62f9d89c135", "result_sha256": "dc993776657ec49090c3bcce2d454783b706434e2092b3b9e1c2c68de8308456", "trigger": "unknown", "validation_state": "w2-unresolved"}, "E8/L1.00": {"B_final": 400, "file": "d2w_case_E8_L1.00.json", "file_bytes": 3857267, "file_sha256": "860614e5a8f91123e514b946fccb99927c6d05d38b362adab3bf047ed52681ed", "manifest_sha256": "462f30c6e05302fe2be5466d9bb9707f25079aa820779db56b2ff3f41d7a8008", "observed_hash": "ec472fe00ca18ab88a5feb851acc781574be16a63d8071c21434b2f56cdc7cc2", "result_sha256": "c661961a61f0b45aefd8e716b7ad0378fcc2d6b443b12fb532e896a134e959fc", "trigger": "unknown", "validation_state": "w2-unresolved"}, "E8/L1.20": {"B_final": 400, "file": "d2w_case_E8_L1.20.json", "file_bytes": 3857353, "file_sha256": "0351be84ae5c17475c060b88ff7332de0dbd4d8912fb2dcefecf8e838e8e7062", "manifest_sha256": "a093ab905a70443f85c05b37b48129761facd8871633e317687cf58acd534d70", "observed_hash": "19845fb5871a4c89d6a345d49df834ce2a7cdafe4c5d3ff2e88f2ff05ac1d274", "result_sha256": "b3086d225660ebd33831098effe38e6223e9a02301ef8fa959860c4934a42723", "trigger": False, "validation_state": "valid"}, "E8/L1.50": {"B_final": 400, "file": "d2w_case_E8_L1.50.json", "file_bytes": 3857449, "file_sha256": "4a5590bc25b70c9a8c9827da94c15f48fd1a417c4a591d30b3f04d6239f693ca", "manifest_sha256": "d65714dec4f43acc121b0befa665de9993c11a39410514b51c50bc55f451d1e2", "observed_hash": "0c84750c67fc4b7eb61a987fb6d59dddedc8b0acd33fe7bb05496daa2448d4f8", "result_sha256": "7789e79a1c77c5bb3f8a328d8f780e38fb1594a8da882509e7739841e6131fd6", "trigger": False, "validation_state": "valid"}},
    failed_attempt=dict(attempt="20261004T102439Z_9bac8f8730", registered_dir="d2w/failed_attempts/20261004T102439Z_9bac8f8730", execution_commit="12980202ee111a26c0a608e7e5bba6caed5302ae", engine_version="0.103.0", archive=dict(file="d2w_cases_12980202ee11_FAILED.zip", sha256="09f9ab0e8ade6c5f0b8cb53c7198bf20e9973618a8146c9647e9b57b9b98b037", bytes=5985),
                        files={"d2w_final_record.json": {"bytes": 6578, "sha256": "d211179ab285577744fdcff8f39ee620105a8b2e910be472de96f1272ea2118f"}, "d2w_lock.json": {"bytes": 1219, "sha256": "9b57d303e6f2c88a976651ba980f03197b2acee961847462c17487cae215033b"}, "d2w_stderr_20261004T102439Z_9bac8f8730.txt": {"bytes": 0, "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}, "d2w_stdout_20261004T102439Z_9bac8f8730.txt": {"bytes": 429, "sha256": "6a5bf2afddae160795a1fbf8794e29839b1404726d5e1c50d567e2c293b85f79"}, "run_20261004T102439Z_9bac8f8730/d2w_run_record.json": {"bytes": 5828, "sha256": "e28a3423eddf45bbcadf818c32f2f3402f01f04fb62fe153fd1147a278670722"}, "run_20261004T102439Z_9bac8f8730/d2w_stdout.log": {"bytes": 377, "sha256": "3b42c2f32ba0b559f20dc76f273c440a1673360420614ac8d6a3aef38abe7a13"}}, stage="inputs", cause="the v1/v2 script compared a run_id the D-2 registry never carries (G_d2_inputs_resolved False; no bank array read, no W2 evaluated); fixed in 0.104.0 (resolve_d2_inputs)"))
REGISTRATION_PINS = ("d4c0_ledger_sha256", "d4c0_outer_receipt_sha256", "d2w_acceptance_sha256", "pseudo_acceptance_sha256", "d2w_context_sha256", "pseudo_paired_sha256", "pseudo_npz_sha256")


def _sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()


def _read(p: str) -> bytes:
    if not os.path.isfile(p) or os.path.islink(p): raise InputContractError(f"registered D4C-0 record missing: {p}")
    return open(p, "rb").read()


def _json(p: str):
    b = _read(p)
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out: raise ValueError(f"duplicate key {k}")
            out[k] = v
        return out
    try: return b, json.loads(b.decode("utf-8"), object_pairs_hook=pairs, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
    except ValueError as ex: raise InputContractError(f"registered D4C-0 record is not strict finite JSON: {p}") from ex


def _payload_sha(doc: dict, key: str) -> str: return _sha(json.dumps({k: v for k, v in doc.items() if k != key}, sort_keys=True, allow_nan=False, ensure_ascii=False).encode("utf-8"))
def _root(root: str) -> str: return os.path.join(os.path.abspath(root), "registered_assets", "d4c0")
def _fail(key: str, what: str): raise InputContractError(f"{key}: {what}")


def _check_files(base: str, expected: dict, key: str) -> dict:
    """Every registered member exists with exactly the constant SHA / bytes; no extra members under the registered directory."""
    found = {}
    for dp, _, fs in os.walk(base):
        for f in fs: p = os.path.join(dp, f); found[os.path.relpath(p, base).replace(os.sep, "/")] = p
    if sorted(found) != sorted(expected): _fail(key, f"registered member set differs from the constants: {sorted(set(found) ^ set(expected))}")
    out = {}
    for rel, p in found.items():
        b = _read(p)
        if _sha(b) != expected[rel]["sha256"] or len(b) != expected[rel]["bytes"]: _fail(key, f"registered member {rel} differs from the accepted original")
        out[rel] = dict(sha256=_sha(b), bytes=len(b))
    return out


def _check_archive(path: str, const: dict, members: dict, key: str) -> dict:
    b = _read(path)
    if _sha(b) != const["sha256"] or len(b) != const["bytes"]: _fail(key, "inner archive bytes differ from the accepted original")
    z = zipfile.ZipFile(path); got = {}
    for i in z.infolist():
        if i.is_dir(): continue
        if i.filename.startswith("/") or ".." in i.filename: _fail(key, "archive member path")
        d = z.read(i.filename); got[i.filename] = dict(sha256=_sha(d), bytes=len(d))
    if got != members: _fail(key, "archive members differ from the registered extracted members")
    return dict(file=os.path.basename(path), sha256=_sha(b), bytes=len(b), members=len(got))


def _check_doc(path: str, const: dict, key: str) -> dict:
    b = _read(path)
    if _sha(b) != const["sha256"] or len(b) != const["bytes"]: _fail(key, f"{os.path.basename(path)} differs from the registered constant")
    return dict(file=os.path.basename(path), sha256=_sha(b), bytes=len(b))


# ------------------------------------------------------------------------------------------------------------------------------------ pseudo
def _check_pseudo(root: str, ctx: TwelveContext) -> dict:
    from .d4_pseudo import load_pseudo_table, verify_pseudo_columns, column_identity
    K = "pseudo"; R = _root(root); base = os.path.join(R, PSEUDO["registered_dir"]); A = PSEUDO["attempt"]; L = PSEUDO["execution_lock"]
    files = _check_files(base, PSEUDO["files"], K); arc = _check_archive(os.path.join(R, "pseudo", "archives", PSEUDO["archive"]["file"]), PSEUDO["archive"], files, K)
    nb = _check_doc(os.path.join(R, "pseudo", "notebooks", PSEUDO["executed_notebook"]["file"]), PSEUDO["executed_notebook"], K)
    ab, acc = _json(os.path.join(R, "pseudo", "acceptance", PSEUDO["acceptance"]["file"])); accf = _check_doc(os.path.join(R, "pseudo", "acceptance", PSEUDO["acceptance"]["file"]), PSEUDO["acceptance"], K)
    md = _check_doc(os.path.join(R, "pseudo", "acceptance", PSEUDO["supplementary"]["audit_md"]["file"]), PSEUDO["supplementary"]["audit_md"], K); v3 = _check_doc(os.path.join(R, "pseudo", "acceptance", PSEUDO["supplementary"]["v3_decision"]["file"]), PSEUDO["supplementary"]["v3_decision"], K)
    lb, lock = _json(os.path.join(base, "d4_pseudo_lock.json")); _, fin = _json(os.path.join(base, "d4_pseudo_final_record.json")); _, rec = _json(os.path.join(base, f"run_{A}", "d4_pseudo_record.json"))
    if _sha(lb) != L["lock_file_sha256"] or lock.get("schema") != "d4_pseudo_launcher_lock_v1" or lock.get("commit") != L["commit"] or lock.get("engine") != L["engine_version"] or lock.get("inventory_sha256") != L["inventory_sha256"] or lock.get("script_sha256") != L["script_sha256"] or lock.get("inventory_script_sha256") != L["script_sha256"] or lock.get("table_file_sha256") != L["table_file_sha256"] or lock.get("table_sha256") != L["table_sha256"] or lock.get("pins_sha256") != L["pins_sha256"] or lock.get("locked_utc") != L["locked_utc"]: _fail(K, "execution lock differs from the registered constants")
    if fin.get("schema") != "d4_pseudo_launcher_final_record_v2" or fin.get("attempt_id") != A or fin.get("lock_sha256") != L["lock_file_sha256"] or fin.get("lock") != lock or fin.get("pseudo_pass") is not True or fin.get("PSEUDO_PASS") is not True or fin.get("exit_code") != 0 or fin.get("stage") != "complete" or fin.get("failures") != [] or fin.get("launcher_fallback") is not False or fin.get("gates_ok") is not True or fin.get("bindings_ok") is not True or fin.get("evidence_ok") is not True: _fail(K, "launcher final record is not the accepted success record of this attempt")
    for pfx in ("precheck", "prelaunch"):
        s = (fin.get("bindings") or {}).get(f"live_source_{pfx}") or {}
        if s.get("head") != L["commit"] or s.get("clean") is not True or s.get("inventory_sha256") != L["inventory_sha256"] or s.get("script_sha256") != L["script_sha256"] or s.get("table_file_sha256") != L["table_file_sha256"] or s.get("pins_sha256") != L["pins_sha256"] or s.get("engine") != L["engine_version"]: _fail(K, f"live source observation ({pfx}) differs from the lock")
    g = rec.get("gates") or {}
    if rec.get("schema") != "d4_pseudo_record_v1" or rec.get("stage") != "complete" or rec.get("failures") != [] or rec.get("selftest") is not False or rec.get("profile") != "production_official" or rec.get("PSEUDO_PASS") is not True or rec.get("required_all_true") is not True or rec.get("required_inventory") != list(PSEUDO_REQUIRED) or sorted(g) != sorted(PSEUDO_REQUIRED) or not all(g.get(k) is True for k in PSEUDO_REQUIRED): _fail(K, "script record is not the accepted success record (REQUIRED gates)")
    if (rec.get("attempt") or {}).get("attempt_id") != A or rec["attempt"].get("launcher_lock_sha256") != L["lock_file_sha256"] or (rec.get("source") or {}).get("script_sha256") != L["script_sha256"] or rec["source"].get("inventory_sha256") != L["inventory_sha256"] or rec["source"].get("pins_sha256") != L["pins_sha256"] or rec["source"].get("engine_version") != L["engine_version"] or rec.get("engine_version") != L["engine_version"]: _fail(K, "script record not bound to this attempt / lock / source")
    t = rec.get("pseudo_table") or {}; gen = rec.get("generation") or {}; cols = rec.get("columns") or {}
    if t.get("table_sha256") != L["table_sha256"] or t.get("n_pseudo") != 2000 or t.get("m") != 1 or t.get("group") != 5001 or t.get("purpose_id") != 400 or t.get("rng_keys") != PSEUDO["rng_keys"] or gen.get("n") != 2000 or gen.get("m") != 1 or gen.get("rng_keys") != PSEUDO["rng_keys"] or gen.get("root_sha256") != PSEUDO["root_sha256"]: _fail(K, "pseudo table / generation identity differs from the constants")
    if cols.get("identity") != PSEUDO["columns"] or cols.get("file") != PSEUDO["npz"]: _fail(K, "column / NPZ identity recorded in the script record differs from the constants")
    env = rec.get("env") or {}
    if not recorded_environment_registered(env, ctx._d["pins"]) or (rec.get("env_gate") or {}).get("versions_ok") is not True or rec["env_gate"].get("pools_ok") is not True: _fail(K, "recorded environment differs from the registered environment (current or registered history)")
    # the ORIGINAL NPZ re-verified against the CONSTANT identity (not the editable record) with the registered pseudo table
    table, _ = load_pseudo_table(os.path.join(os.path.abspath(root), "d", "d4_pseudo_table.json"), L["table_sha256"])
    npz = os.path.join(base, f"run_{A}", PSEUDO["npz"]["file"]); c = verify_pseudo_columns(npz, PSEUDO["columns"], table, PSEUDO["npz"])
    if c["n"] != 2000 or column_identity(c) != PSEUDO["columns"]: _fail(K, "registered NPZ columns differ from the constant identity")
    S = acc.get("subject") or {}
    if acc.get("decision") != PSEUDO["acceptance"]["decision"] or acc.get("formal_pseudo_generation_accepted") is not True or acc.get("requires_pseudo_regeneration") is not False or S.get("attempt") != A or S.get("execution_commit") != L["commit"] or S.get("engine") != L["engine_version"] or S.get("archive_sha256") != PSEUDO["archive"]["sha256"] or S.get("files") != {k: v["sha256"] for k, v in PSEUDO["files"].items()} or S.get("columns") != PSEUDO["columns"] or S.get("npz") != PSEUDO["npz"] or S.get("root_sha256") != PSEUDO["root_sha256"] or (S.get("execution_lock") or {}).get("commit") != L["commit"]: _fail(K, "acceptance document does not name the registered originals / identities")
    return dict(attempt=A, registered_dir=PSEUDO["registered_dir"], execution_lock=copy.deepcopy(L), records=files, inner_archive=arc, executed_notebook=nb, acceptance=dict(accf, decision=acc["decision"]), supplementary=dict(audit_md=md, v3_decision=v3), columns=copy.deepcopy(PSEUDO["columns"]), npz=copy.deepcopy(PSEUDO["npz"]), root_sha256=PSEUDO["root_sha256"], rng_keys=copy.deepcopy(PSEUDO["rng_keys"]),
                resources=dict(seconds_script=rec["seconds"], seconds_launcher=fin["seconds_total"], stages_peak_rss_mb=rec["stages_peak_rss_mb"], ram_total_bytes=(fin.get("ram") or {}).get("total_bytes")), environment={k: env[k] for k in ("python", "numpy", "scipy", "healpy", "camb", "pot")})


# ------------------------------------------------------------------------------------------------------------------------------------ D-2W
def _check_d2w(root: str, ctx: TwelveContext) -> dict:
    K = "d2w"; R = _root(root); base = os.path.join(R, D2W["registered_dir"]); A = D2W["attempt"]; L = D2W["execution_lock"]; d2l = ctx._d["d2_ledger"]
    files = _check_files(base, D2W["files"], K); arc = _check_archive(os.path.join(R, "d2w", "archives", D2W["archive"]["file"]), D2W["archive"], files, K)
    nb = _check_doc(os.path.join(R, "d2w", "notebooks", D2W["executed_notebook"]["file"]), D2W["executed_notebook"], K)
    ab, acc = _json(os.path.join(R, "d2w", "acceptance", D2W["acceptance"]["file"])); accf = _check_doc(os.path.join(R, "d2w", "acceptance", D2W["acceptance"]["file"]), D2W["acceptance"], K); md = _check_doc(os.path.join(R, "d2w", "acceptance", D2W["audit_md"]["file"]), D2W["audit_md"], K)
    lb, lock = _json(os.path.join(base, "d2w_lock.json")); _, fin = _json(os.path.join(base, "d2w_final_record.json")); _, rec = _json(os.path.join(base, f"run_{A}", "d2w_run_record.json")); _, cr = _json(os.path.join(base, f"run_{A}", "d2w_context_record.json"))
    if _sha(lb) != L["lock_file_sha256"] or lock.get("schema") != "d2w_launcher_lock_v1" or lock.get("commit") != L["commit"] or lock.get("engine") != L["engine_version"] or lock.get("inventory_sha256") != L["inventory_sha256"] or lock.get("script_sha256") != L["script_sha256"] or lock.get("inventory_script_sha256") != L["script_sha256"] or lock.get("ledger_file_sha256") != L["ledger_file_sha256"] or lock.get("asset_file_sha256") != L["asset_file_sha256"] or lock.get("pins_sha256") != L["pins_sha256"] or lock.get("locked_utc") != L["locked_utc"] or lock.get("d2_run_roots") != L["d2_run_roots"] or lock.get("stage_local") is not True: _fail(K, "execution lock differs from the registered constants")
    if lock["ledger_file_sha256"] != ctx._d["d2_ledger_sha256"]: _fail(K, "the execution lock's D-2 ledger file differs from the current registered D-2 ledger")
    for f in ("E2", "E7", "E8"):
        if L["d2_run_roots"][f].rstrip("/") != d2l["families"][f]["run_root"].rstrip("/") + "/out/d2": _fail(K, f"{f}: locked D-2 run root differs from the registered D-2 ledger run root")
    if fin.get("schema") != "d2w_launcher_final_record_v2" or fin.get("attempt_id") != A or fin.get("lock_sha256") != L["lock_file_sha256"] or fin.get("lock") != lock or fin.get("d2w_pass") is not True or fin.get("D2W_PASS") is not True or fin.get("exit_code") != 0 or fin.get("stage") != "complete" or fin.get("failures") != [] or fin.get("launcher_fallback") is not False or fin.get("gates_ok") is not True or fin.get("bindings_ok") is not True or fin.get("evidence_ok") is not True or fin.get("context_sha256") != D2W["context_sha256"]: _fail(K, "launcher final record is not the accepted success record of this attempt")
    for pfx in ("precheck", "prelaunch"):
        s = (fin.get("bindings") or {}).get(f"live_source_{pfx}") or {}
        if s.get("head") != L["commit"] or s.get("clean") is not True or s.get("inventory_sha256") != L["inventory_sha256"] or s.get("script_sha256") != L["script_sha256"] or s.get("ledger_file_sha256") != L["ledger_file_sha256"] or s.get("asset_file_sha256") != L["asset_file_sha256"] or s.get("pins_sha256") != L["pins_sha256"] or s.get("engine") != L["engine_version"]: _fail(K, f"live source observation ({pfx}) differs from the lock")
    g = rec.get("gates") or {}
    if rec.get("schema") != "d2w_run_record_v1" or rec.get("stage") != "complete" or rec.get("failures") != [] or rec.get("selftest") is not False or rec.get("profile") != "production_official" or rec.get("D2W_PASS") is not True or rec.get("required_all_true") is not True or rec.get("required_inventory") != list(D2W_REQUIRED) or sorted(g) != sorted(D2W_REQUIRED) or not all(g.get(k) is True for k in D2W_REQUIRED): _fail(K, "script record is not the accepted success record (REQUIRED gates)")
    if (rec.get("attempt") or {}).get("attempt_id") != A or rec["attempt"].get("launcher_lock_sha256") != L["lock_file_sha256"] or (rec.get("source") or {}).get("script_sha256") != L["script_sha256"] or rec["source"].get("inventory_sha256") != L["inventory_sha256"] or rec["source"].get("pins_sha256") != L["pins_sha256"] or rec["source"].get("engine_version") != L["engine_version"]: _fail(K, "script record not bound to this attempt / lock / source")
    env = rec.get("env") or {}
    if not recorded_environment_registered(env, ctx._d["pins"]) or (rec.get("env_gate") or {}).get("versions_ok") is not True or rec["env_gate"].get("pools_ok") is not True: _fail(K, "recorded environment differs from the registered environment (current or registered history)")
    inp = rec.get("inputs") or {}
    if inp.get("cases") != list(CANON_CASES) or inp.get("resolution_failures") != []: _fail(K, "run record case set / input resolution")
    for f in ("E2", "E7", "E8"):
        e = (inp.get("d2_roots") or {}).get(f) or {}
        if e.get("run_id") != d2l["families"][f]["run_id"] or e.get("registry_sha256") != d2l["families"][f]["records"]["bank_registry_sha256"] or e.get("w2_units") != 9: _fail(K, f"{f}: run record input binding differs from the registered D-2 ledger")
    C = rec.get("context") or {}; cases = C.get("cases") or {}
    if C.get("context_sha256") != D2W["context_sha256"] or C.get("asset_sha256") != D2W["asset_sha256"] or sorted(cases) != sorted(CANON_CASES): _fail(K, "run record context identity")
    pe = rec.get("published_evidence") or {}; units_bound = 0
    for k in CANON_CASES:
        c = D2W["cases"][k]; s = cases[k]; e = pe.get(c["file"]) or {}
        if s.get("manifest_sha256") != c["manifest_sha256"] or s.get("result_sha256") != c["result_sha256"] or s.get("trigger") != c["trigger"] or s.get("validation_state") != c["validation_state"] or s.get("B_final") != c["B_final"]: _fail(K, f"{k}: run summary differs from the registered constant decision")
        rel = f"run_{A}/cases/{c['file']}"
        if e.get("sha256") != c["file_sha256"] or e.get("bytes") != c["file_bytes"] or files[rel] != dict(sha256=c["file_sha256"], bytes=c["file_bytes"]): _fail(K, f"{k}: published case file identity")
        _, d = _json(os.path.join(base, rel)); fam, size = k.split("/")
        if d.get("schema") != "d2w_case_record_v1" or d.get("key") != k or d.get("family") != fam or d.get("size_id") != size or d.get("asset_sha256") != D2W["asset_sha256"] or d.get("manifest_sha256") != c["manifest_sha256"] or d.get("result_sha256") != c["result_sha256"] or (d.get("inputs") or {}).get("formal") is not True: _fail(K, f"{k}: case record identity")
        dd = d.get("decision") or {}
        if dd.get("trigger") != c["trigger"] or dd.get("validation_state") != c["validation_state"] or dd.get("B_final") != c["B_final"] or dd.get("observed_hash") != c["observed_hash"] or dd.get("distance_kind") != "exact_pot_w2": _fail(K, f"{k}: case record decision differs from the registered constant")
        for u, v in (d["inputs"].get("units") or {}).items():
            if d2l["families"][fam]["units"].get(u, {}).get("manifest_sha256") != v.get("manifest_sha256") or (v.get("bank_identity_f64") or {}).get("K") != 2000 or v["bank_identity_f64"].get("m") != 100 or v["bank_identity_f64"].get("rows") != 200000 or (v.get("bank_identity_f32") or {}).get("rows") != 200000: _fail(K, f"{k}: unit {u} not the registered formal D-2 W2 unit")
            units_bound += 1
    if units_bound != 27 or pe.get("d2w_context_record.json") != files[f"run_{A}/d2w_context_record.json"]: _fail(K, "27 registered units / context record evidence")
    if cr.get("schema") != "d2w_context_record_v1" or cr.get("context_sha256") != D2W["context_sha256"] or cr.get("asset_sha256") != D2W["asset_sha256"] or cr.get("n_cases") != 9 or sorted(cr.get("case_records") or {}) != sorted(CANON_CASES) or any((cr["case_records"][k].get("manifest_sha256"), cr["case_records"][k].get("result_sha256"), cr["case_records"][k].get("trigger"), cr["case_records"][k].get("validation_state"), cr["case_records"][k].get("B_final")) != (D2W["cases"][k]["manifest_sha256"], D2W["cases"][k]["result_sha256"], D2W["cases"][k]["trigger"], D2W["cases"][k]["validation_state"], D2W["cases"][k]["B_final"]) for k in CANON_CASES): _fail(K, "context record differs from the registered constants")
    S = acc.get("subject") or {}
    if acc.get("decision") != D2W["acceptance"]["decision"] or acc.get("formal_D2W_run_accepted") is not True or acc.get("requires_D2W_rerun") is not False or S.get("attempt") != A or S.get("execution_commit") != L["commit"] or S.get("engine") != L["engine_version"] or S.get("archive") != D2W["archive"]["sha256"] or {k: v.get("sha256") for k, v in (S.get("files") or {}).items()} != {k: v["sha256"] for k, v in D2W["files"].items()} or S.get("context_sha256") != D2W["context_sha256"] or (S.get("execution_lock") or {}).get("commit") != L["commit"]: _fail(K, "acceptance document does not name the registered originals / identities")
    for k in CANON_CASES:
        a = (S.get("cases") or {}).get(k) or {}; c = D2W["cases"][k]
        if (a.get("file_identity") or {}).get("sha256") != c["file_sha256"] or a.get("manifest_sha256") != c["manifest_sha256"] or a.get("result_sha256") != c["result_sha256"] or (a.get("decision") or {}).get("trigger") != c["trigger"] or a["decision"].get("validation_state") != c["validation_state"] or a["decision"].get("B_final") != c["B_final"]: _fail(K, f"{k}: acceptance decision differs from the registered constant")
    if ((acc.get("executed_notebooks") or {}).get("d2w") or {}).get("sha256") != D2W["executed_notebook"]["sha256"]: _fail(K, "acceptance does not name the registered executed notebook")
    # the failed attempt: separate, immutable failure history; never a success source
    FA = D2W["failed_attempt"]; fbase = os.path.join(R, FA["registered_dir"]); ffiles = _check_files(fbase, FA["files"], "d2w_failed"); farc = _check_archive(os.path.join(R, "d2w", "archives", FA["archive"]["file"]), FA["archive"], ffiles, "d2w_failed")
    _, ffin = _json(os.path.join(fbase, "d2w_final_record.json")); _, frec = _json(os.path.join(fbase, f"run_{FA['attempt']}", "d2w_run_record.json")); _, flock = _json(os.path.join(fbase, "d2w_lock.json"))
    if ffin.get("attempt_id") != FA["attempt"] or ffin.get("d2w_pass") is not False or frec.get("D2W_PASS") is not False or frec.get("stage") != FA["stage"] or (frec.get("gates") or {}).get("G_d2_inputs_resolved") is not False or flock.get("commit") != FA["execution_commit"] or flock.get("engine") != FA["engine_version"]: _fail("d2w_failed", "the registered failed attempt is not the recorded failure (stage inputs, no success)")
    PF = acc.get("previous_failure") or {}
    if PF.get("attempt") != FA["attempt"] or PF.get("archive_sha256") != FA["archive"]["sha256"] or PF.get("files") != {k: v["sha256"] for k, v in FA["files"].items()} or PF.get("scientific_result_accepted") is not False: _fail("d2w_failed", "acceptance does not record the failed attempt as failure history")
    return dict(attempt=A, registered_dir=D2W["registered_dir"], execution_lock=copy.deepcopy(L), records=files, inner_archive=arc, executed_notebook=nb, acceptance=dict(accf, decision=acc["decision"]), audit_md=md, context_sha256=D2W["context_sha256"], asset_sha256=D2W["asset_sha256"], cases=copy.deepcopy(D2W["cases"]), units_bound=units_bound,
                registry_sha256={f: d2l["families"][f]["records"]["bank_registry_sha256"] for f in ("E2", "E7", "E8")}, summary=dict(valid_false=[k for k in CANON_CASES if D2W["cases"][k]["validation_state"] == "valid"], unresolved_unknown=[k for k in CANON_CASES if D2W["cases"][k]["validation_state"] == "w2-unresolved"], technical_failures=0),
                resources=dict(seconds_script=rec["seconds"], seconds_launcher=fin["seconds_total"], evaluation_seconds=rec["timings"]["evaluation_seconds"], stages_peak_rss_mb=rec["stages_peak_rss_mb"], ram_total_bytes=(fin.get("ram") or {}).get("total_bytes"), staging_bytes=(fin.get("staging") or {}).get("input_bytes")), environment={k: env[k] for k in ("python", "numpy", "scipy", "healpy", "camb", "pot")},
                failed_attempt=dict(attempt=FA["attempt"], registered_dir=FA["registered_dir"], execution_commit=FA["execution_commit"], engine_version=FA["engine_version"], inner_archive=farc, records=ffiles, stage=FA["stage"], cause=FA["cause"], success=False))


# ------------------------------------------------------------------------------------------------------------------------------------ ledger / receipt
def build_d4c0_ledger(phaseb_root: str, ctx: TwelveContext) -> dict:
    """Deterministic ledger of the accepted pseudo generation and D-2W run (module docstring); raises on any inconsistency; never repairs a record."""
    ctx = _require_ctx(ctx); root = os.path.abspath(phaseb_root)
    if os.path.realpath(root) != os.path.realpath(ctx.root): raise InputContractError("the registered D4C-0 records must be read from the root of the verified context")
    p = _check_pseudo(root, ctx); d = _check_d2w(root, ctx)
    doc = dict(schema=LEDGER_SCHEMA, pseudo=p, d2w=d, canonical_cases=list(CANON_CASES), registered_d2=dict(ledger_file_sha256=ctx._d["d2_ledger_sha256"], registry_sha256=d["registry_sha256"]), shared_null_asset_sha256=D2W["asset_sha256"],
               statement="REGISTERED (scoped): the accepted formal pseudo columns (n = 2000, m = 1; one ordered pair shared by all families; commit 12980202 / engine 0.103.0) and the accepted formal D-2W nine-case W2 context (commit f3aec793 / engine 0.104.0; 5 valid-False, 4 w2-unresolved-unknown, 0 technical failures), registered as their original bytes and bound to their own execution locks; the failed D-2W attempt is kept as failure history. The W2 unknowns remain W2-branch uncertainty (never technical failure or False); D-4 must combine them with the per-pseudo event-ratio branch and the registered twelve-position completion. Calibration, thresholds, labels and noise remain separately gated.")
    doc["ledger_sha256"] = _payload_sha(doc, "ledger_sha256"); return doc


def verify_d4c0_ledger(doc: dict, phaseb_root: str, ctx: TwelveContext) -> dict:
    if not isinstance(doc, dict) or doc.get("schema") != LEDGER_SCHEMA: raise InputContractError("D4C-0 ledger schema")
    if doc.get("ledger_sha256") != _payload_sha(doc, "ledger_sha256"): raise InputContractError("D4C-0 ledger payload SHA")
    fresh = build_d4c0_ledger(phaseb_root, ctx)
    if doc != fresh: raise InputContractError("D4C-0 ledger differs from its re-derivation from the registered originals")
    return copy.deepcopy(fresh)


def _require_registration_pins(ctx: TwelveContext) -> dict:
    """All registration pins present and equal to the module constants (wrong / missing / null refused) - the common guard of every registered load."""
    pins = ctx._d["pins"]; want = dict(d2w_acceptance_sha256=D2W["acceptance"]["sha256"], pseudo_acceptance_sha256=PSEUDO["acceptance"]["sha256"], d2w_context_sha256=D2W["context_sha256"], pseudo_paired_sha256=PSEUDO["columns"]["paired_sha256"], pseudo_npz_sha256=PSEUDO["npz"]["sha256"])
    for k, v in want.items():
        if pins.get(k) != v: raise InputContractError(f"registered D4C-0 identity differs from the pins ({k} must equal the accepted constant; wrong / missing / null refused)")
    for k in ("d4c0_ledger_sha256", "d4c0_outer_receipt_sha256"):
        if not (isinstance(pins.get(k), str) and len(pins[k]) == 64): raise InputContractError(f"registered D4C-0 pin {k} missing")
    return {k: pins[k] for k in REGISTRATION_PINS}


def load_registered_d4c0_ledger(phaseb_root: str, ctx: TwelveContext) -> dict:
    """The committed registered_assets/d4c0/d4c0_ledger.json: pins carry the acceptance / context / column identities, payload identity == pins (d4c0_ledger_sha256), content == re-derivation."""
    ctx = _require_ctx(ctx); root = os.path.abspath(phaseb_root)
    if os.path.realpath(root) != os.path.realpath(ctx.root): raise InputContractError("the registered D4C-0 ledger must be read from the root of the verified context")
    pins = _require_registration_pins(ctx); b, doc = _json(os.path.join(_root(root), "d4c0_ledger.json"))
    if doc.get("ledger_sha256") != pins["d4c0_ledger_sha256"]: raise InputContractError("registered D4C-0 ledger identity differs from the pins")
    out = verify_d4c0_ledger(doc, root, ctx); out["_file_sha256"] = _sha(b); return out


def build_d4c0_outer_receipt(phaseb_root: str, ctx: TwelveContext) -> dict:
    ctx = _require_ctx(ctx); root = os.path.abspath(phaseb_root)
    if os.path.realpath(root) != os.path.realpath(ctx.root): raise InputContractError("the registered D4C-0 receipt must be read from the root of the verified context")
    L = load_registered_d4c0_ledger(root, ctx); p, d = L["pseudo"], L["d2w"]
    doc = dict(schema=RECEIPT_SCHEMA, ledger=dict(payload_sha256=L["ledger_sha256"], file_sha256=L["_file_sha256"], schema=LEDGER_SCHEMA),
               pseudo=dict(attempt=p["attempt"], execution_lock=copy.deepcopy(p["execution_lock"]), inner_archive_sha256=p["inner_archive"]["sha256"], executed_notebook_sha256=p["executed_notebook"]["sha256"], acceptance=copy.deepcopy(p["acceptance"]), columns=copy.deepcopy(p["columns"]), npz=copy.deepcopy(p["npz"]), root_sha256=p["root_sha256"], registered_dir=p["registered_dir"]),
               d2w=dict(attempt=d["attempt"], execution_lock=copy.deepcopy(d["execution_lock"]), inner_archive_sha256=d["inner_archive"]["sha256"], executed_notebook_sha256=d["executed_notebook"]["sha256"], acceptance=copy.deepcopy(d["acceptance"]), context_sha256=d["context_sha256"], asset_sha256=d["asset_sha256"], cases={k: dict(file_sha256=v["file_sha256"], manifest_sha256=v["manifest_sha256"], result_sha256=v["result_sha256"], trigger=v["trigger"], validation_state=v["validation_state"], B_final=v["B_final"]) for k, v in d["cases"].items()}, summary=copy.deepcopy(d["summary"]), registered_dir=d["registered_dir"], failed_attempt=dict(attempt=d["failed_attempt"]["attempt"], inner_archive_sha256=d["failed_attempt"]["inner_archive"]["sha256"], execution_commit=d["failed_attempt"]["execution_commit"], success=False)),
               pins_binding={k: ctx._d["pins"][k] for k in ("d2w_acceptance_sha256", "pseudo_acceptance_sha256", "d2w_context_sha256", "pseudo_paired_sha256", "pseudo_npz_sha256", "d4_pseudo_table_sha256", "config_map_sha256", "covariance_receipt_sha256")},
               statement="ACCEPTED (scoped): the registered pseudo columns and the registered D-2W context are the registered inputs of the D-4 calibration (D4C-1); this receipt is the auditor's scoped acceptance of the registered originals (post-run acceptances 08efa1d1... and c9506e0b...), not a re-read of the production banks nor an exact-OT re-execution; calibration, usable, target, labels and noise remain separately gated.")
    doc["receipt_sha256"] = _payload_sha(doc, "receipt_sha256"); return doc


def verify_d4c0_outer_receipt(doc: dict, phaseb_root: str, ctx: TwelveContext) -> dict:
    if not isinstance(doc, dict) or doc.get("schema") != RECEIPT_SCHEMA: raise InputContractError("D4C-0 outer receipt schema")
    if doc.get("receipt_sha256") != _payload_sha(doc, "receipt_sha256"): raise InputContractError("D4C-0 outer receipt payload SHA")
    fresh = build_d4c0_outer_receipt(phaseb_root, ctx)
    if doc != fresh: raise InputContractError("D4C-0 outer receipt differs from its re-derivation from the registered records")
    return copy.deepcopy(fresh)


def load_registered_d4c0_outer_receipt(phaseb_root: str, ctx: TwelveContext) -> dict:
    ctx = _require_ctx(ctx); root = os.path.abspath(phaseb_root)
    if os.path.realpath(root) != os.path.realpath(ctx.root): raise InputContractError("the registered D4C-0 receipt must be read from the root of the verified context")
    pins = _require_registration_pins(ctx); b, doc = _json(os.path.join(_root(root), "d4c0_outer_receipt.json"))
    if doc.get("receipt_sha256") != pins["d4c0_outer_receipt_sha256"]: raise InputContractError("registered D4C-0 outer receipt identity differs from the pins")
    out = verify_d4c0_outer_receipt(doc, root, ctx); out["_file_sha256"] = _sha(b); return out


# ------------------------------------------------------------------------------------------------------------------------------------ consumer loaders
def load_registered_w2_context(phaseb_root: str, ctx: TwelveContext):
    """The registered D-2W W2Context for consumers (D-4): ledger + receipt loaded under the pin guards (acceptance / context / ledger / receipt pins), the nine ORIGINAL case
    record files authenticated byte-for-byte against the ledger constants, then the typed context RESTORED by w2_cases.restore_w2_context (replay of stop / validation / trigger
    from the stored evidence against the registered shared-null asset; exact OT not re-run) with expected_context_sha256 = the AUTHENTICATED PIN d2w_context_sha256 (== the
    constant), require_formal=True and the canonical nine keys; every re-issued decision must equal the registered constant (the four unknowns stay unknown). Returns
    (W2Context, view) where view carries the registration identities."""
    from .w2_cases import restore_w2_context, registered_shared_null_asset
    ctx = _require_ctx(ctx); root = os.path.abspath(phaseb_root); L = load_registered_d4c0_ledger(root, ctx); rc = load_registered_d4c0_outer_receipt(root, ctx); pins = ctx._d["pins"]
    if rc["ledger"]["payload_sha256"] != L["ledger_sha256"] or pins["d2w_context_sha256"] != D2W["context_sha256"]: raise InputContractError("registered D-2W receipt / context pin inconsistent")
    base = os.path.join(_root(root), L["d2w"]["registered_dir"], f"run_{D2W['attempt']}", "cases"); recs = []
    for k in CANON_CASES:
        c = D2W["cases"][k]; b = _read(os.path.join(base, c["file"]))
        if _sha(b) != c["file_sha256"] or len(b) != c["file_bytes"]: raise InputContractError(f"{k}: registered case record bytes differ from the accepted original")
        recs.append(json.loads(b.decode("utf-8")))
    asset = registered_shared_null_asset(root)
    if asset.sha256 != D2W["asset_sha256"]: raise InputContractError("registered shared-null asset differs from the D-2W execution asset")
    w2ctx = restore_w2_context(recs, asset, expected_context_sha256=pins["d2w_context_sha256"], require_formal=True)
    if sorted(w2ctx.decisions) != sorted(CANON_CASES) or w2ctx.context_sha256 != D2W["context_sha256"]: raise InputContractError("restored D-2W context differs from the registered identity")
    for k in CANON_CASES:
        d = w2ctx.decisions[k]; c = D2W["cases"][k]
        if d.trigger != c["trigger"] or d.validation_state != c["validation_state"] or int(d.B_final) != c["B_final"] or d.observed_hash != c["observed_hash"] or d.distance_kind != "exact_pot_w2": raise InputContractError(f"{k}: re-issued decision differs from the registered constant decision")
    view = dict(attempt=D2W["attempt"], execution_lock=copy.deepcopy(D2W["execution_lock"]), context_sha256=w2ctx.context_sha256, asset_sha256=asset.sha256, cases={k: dict(trigger=w2ctx.decisions[k].trigger, validation_state=w2ctx.decisions[k].validation_state, B_final=int(w2ctx.decisions[k].B_final)) for k in CANON_CASES}, ledger_sha256=L["ledger_sha256"], receipt_sha256=rc["receipt_sha256"], acceptance_sha256=D2W["acceptance"]["sha256"],
                summary=copy.deepcopy(L["d2w"]["summary"]), scope="registered D-2W W2 context: W2 branch only (trigger False / unknown); the unknowns are W2-branch uncertainty, to be combined by D-4 with the per-pseudo event-ratio branch and the registered twelve-position completion; not a calibration result")
    return w2ctx, view


def load_registered_pseudo_columns(phaseb_root: str, ctx: TwelveContext) -> dict:
    """The registered pseudo columns for consumers (D-4): ledger + receipt under the pin guards (acceptance / paired / NPZ pins), the ORIGINAL NPZ authenticated byte-for-byte
    (pin pseudo_npz_sha256 == constant) and re-verified by d4_pseudo.verify_pseudo_columns against the CONSTANT identity with the registered pseudo table (n = 2000, m = 1,
    dtypes, ordered paired rows, UIDs, column / paired SHAs; pin pseudo_paired_sha256 == constant). Returns the columns (T1 / T2 / AX / PL / cid / uids / n) plus a view."""
    from .d4_pseudo import load_pseudo_table, verify_pseudo_columns, column_identity
    ctx = _require_ctx(ctx); root = os.path.abspath(phaseb_root); L = load_registered_d4c0_ledger(root, ctx); rc = load_registered_d4c0_outer_receipt(root, ctx); pins = ctx._d["pins"]
    if rc["ledger"]["payload_sha256"] != L["ledger_sha256"] or pins["pseudo_npz_sha256"] != PSEUDO["npz"]["sha256"] or pins["pseudo_paired_sha256"] != PSEUDO["columns"]["paired_sha256"]: raise InputContractError("registered pseudo receipt / pins inconsistent")
    npz = os.path.join(_root(root), L["pseudo"]["registered_dir"], f"run_{PSEUDO['attempt']}", PSEUDO["npz"]["file"]); b = _read(npz)
    if _sha(b) != pins["pseudo_npz_sha256"] or len(b) != PSEUDO["npz"]["bytes"]: raise InputContractError("registered pseudo NPZ bytes differ from the accepted original")
    table, _ = load_pseudo_table(os.path.join(root, "d", "d4_pseudo_table.json"), pins.get("d4_pseudo_table_sha256"))
    cols = verify_pseudo_columns(npz, PSEUDO["columns"], table, PSEUDO["npz"]); idn = column_identity(cols)
    if idn != PSEUDO["columns"] or idn["paired_sha256"] != pins["pseudo_paired_sha256"] or cols["n"] != 2000: raise InputContractError("registered pseudo columns differ from the constant identity")
    cols = dict(cols, identity=idn, view=dict(attempt=PSEUDO["attempt"], execution_lock=copy.deepcopy(PSEUDO["execution_lock"]), npz=copy.deepcopy(PSEUDO["npz"]), root_sha256=PSEUDO["root_sha256"], rng_keys=copy.deepcopy(PSEUDO["rng_keys"]), ledger_sha256=L["ledger_sha256"], receipt_sha256=rc["receipt_sha256"], acceptance_sha256=PSEUDO["acceptance"]["sha256"], order="paired (T1_p, T2_p) in generation order; one shared ordered pair per pseudo for ALL families"))
    return cols
