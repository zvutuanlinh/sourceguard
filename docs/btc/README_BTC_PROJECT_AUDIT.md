# EXAMTRUST AI — BTC PROJECT AUDIT GUIDE

> **Mục đích:** tài liệu này dành cho BTC/BGK kiểm tra trực tiếp dự án từ **Google Drive + GitHub + RAW + evidence lịch sử + pipeline tái kiểm chứng**.  
> **Nguyên tắc:** mỗi cell chỉ kiểm tra một nhóm thông tin, đọc trực tiếp từ dự án và in/hiển thị nội dung; không viết lại lịch sử, không sửa evidence, không force-push, không chạy Gemini/OCR/segmentation live.

---

## 0. PHẠM VI KIỂM TRA

BTC có thể dùng tài liệu này để xác minh các lớp bằng chứng sau:

1. **Git authority:** branch, HEAD, remote, tags, commit graph, nội dung commit.
2. **Drive authority:** RAW P06/P07/P08, historical evidence, checkpoint, receipts, reproducibility runs.
3. **Final question lineage:** Source Unit universe → human selection → composition → contract → pregen → Candidate V1 fail → Candidate V2 pass → teacher approval → READY_FOR_USE.
4. **Reusable pipeline:** pipeline `.py` chạy lại từ RAW ở Colab trắng.
5. **Tính toàn vẹn:** SHA256, tag target, commit parent, remote main, không mutation lịch sử.

Các mốc đã được xác nhận gần nhất:

```text
Project closure checkpoint:
b0196cdcaf365b808fcb91b1cd85c2e54f4e0903
tag: examtrust-project-closure-v1

R2 remote cumulative history head before merge:
187b7972348f6279c4ba950577ab4092c4601e97

Final P06/P07/P08 question checkpoint:
f56338a14a21e063de3d68eb31c0a6242ad29d18
tag: btc-final-p06-p07-p08-question-v1

History integration merge:
0e4b3624a3a905ca117918d8609fcb886519fff8

Reusable RAW-to-READY pipeline commit / current verified remote main:
1d2cabed1e6f669a841399afc92c16f4b13bca0f

Reusable pipeline SHA256:
4a2b7a6bf82251ea289139481d1e68c142256a94532d5872733225fea18d3978

Final pipeline Git receipt SHA256:
c8e097d41b348096b774d1346c5dcd5762a73fdd960e17ba4e28d5f18411c6ae
```

---

# CELL 01 — MOUNT GOOGLE DRIVE

**Mục đích:** gắn Google Drive của chủ dự án vào runtime. Không sửa file.

```python
from google.colab import drive
from pathlib import Path

drive.mount("/content/drive", force_remount=False)

MYDRIVE = Path("/content/drive/MyDrive")
print("MYDRIVE =", MYDRIVE)
print("EXISTS  =", MYDRIVE.exists())

assert MYDRIVE.exists(), "HOLD: MyDrive chưa mount thành công"
```

---

# CELL 02 — KHAI BÁO ĐƯỜNG DẪN DỰ ÁN

**Mục đích:** xác định repo SourceGuard, vùng BTC isolated và checkpoint chính.

```python
from pathlib import Path

MYDRIVE = Path("/content/drive/MyDrive")

REPO = MYDRIVE / "SourceGuard_Git" / "sourceguard"
BTC_ROOT = MYDRIVE / "EXAMTRUST_BTC_FINAL_ISOLATED_V1"

QUESTION_CP = (
    BTC_ROOT
    / "05_MANIFEST"
    / "BTC_FINAL_QUESTION_PIPELINE_CHECKPOINT_V1"
)

REUSE_CP = (
    QUESTION_CP
    / "REUSABLE_RAW_TO_READY_PIPELINE_V1"
)

print("REPO        =", REPO)
print("BTC_ROOT    =", BTC_ROOT)
print("QUESTION_CP =", QUESTION_CP)
print("REUSE_CP    =", REUSE_CP)

assert (REPO / ".git").exists(), "HOLD: SourceGuard repo không tồn tại"
assert BTC_ROOT.exists(), "HOLD: BTC isolated workspace không tồn tại"
assert QUESTION_CP.exists(), "HOLD: final-question checkpoint không tồn tại"
assert REUSE_CP.exists(), "HOLD: reusable-pipeline checkpoint không tồn tại"
```

---

# CELL 03 — KẾT NỐI GITHUB QUA COLAB SECRET

**Mục đích:** kiểm tra `GITHUB_TOKEN` tồn tại nhưng **không in token**. Tạo `GIT_ASKPASS` tạm cho các lệnh cần xác thực.

```python
from google.colab import userdata
from pathlib import Path
import tempfile, os

token = userdata.get("GITHUB_TOKEN")
assert token, "HOLD: thiếu GITHUB_TOKEN trong Colab Secret"

TMP_AUTH = Path(tempfile.mkdtemp(prefix="btc_git_auth_"))
ASKPASS = TMP_AUTH / "askpass.sh"

ASKPASS.write_text(
    "\n".join([
        "#!/bin/sh",
        'case "$1" in',
        '  *Username*) printf \'%s\\n\' "${GITHUB_USERNAME}" ;;',
        '  *Password*) printf \'%s\\n\' "${GITHUB_TOKEN}" ;;',
        "  *) printf '\\n' ;;",
        "esac",
        "",
    ]),
    encoding="utf-8"
)
ASKPASS.chmod(0o700)

GIT_ENV = os.environ.copy()
GIT_ENV["GIT_ASKPASS"] = str(ASKPASS)
GIT_ENV["GIT_TERMINAL_PROMPT"] = "0"
GIT_ENV["GITHUB_USERNAME"] = "zvutuanlinh"
GIT_ENV["GITHUB_TOKEN"] = token

print("GITHUB_TOKEN = AVAILABLE")
print("TOKEN VALUE  = [HIDDEN]")
print("ASKPASS      =", ASKPASS)
```

---

# CELL 04 — GIT LOCAL AUTHORITY

**Mục đích:** show branch, HEAD, status, remote URL. Chỉ đọc.

```python
import subprocess

def git(args, check=True, env=None):
    p = subprocess.run(
        ["git"] + args,
        cwd=str(REPO),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
    )
    if check and p.returncode != 0:
        print(p.stdout)
        raise RuntimeError("HOLD: git " + " ".join(args))
    return p.stdout.strip()

print("BRANCH =", git(["branch", "--show-current"]))
print("HEAD   =", git(["rev-parse", "HEAD"]))
print()
print("REMOTE:")
print(git(["remote", "-v"]))
print()
print("STATUS:")
status = git(["status", "--short"])
print(status if status else "CLEAN TRACKED/WORKTREE STATUS")
```

---

# CELL 05 — FETCH REMOTE VÀ ĐỐI CHIẾU LOCAL/REMOTE

**Mục đích:** đọc remote mới nhất, không merge/rebase/reset/push.

```python
print(git(["fetch", "--prune", "origin", "main"], env=GIT_ENV))

local_head = git(["rev-parse", "HEAD"])
remote_head = git(["rev-parse", "origin/main"])
counts = git(["rev-list", "--left-right", "--count", "HEAD...origin/main"])

print("LOCAL HEAD  =", local_head)
print("REMOTE HEAD =", remote_head)
print("HEAD...origin/main =", counts)
```

**Mốc kỳ vọng tại lần đóng gói hiện tại:**

```text
1d2cabed1e6f669a841399afc92c16f4b13bca0f
```

---

# CELL 06 — SHOW FULL GIT GRAPH VÀ TAGS

**Mục đích:** BTC xem quá trình phát triển qua commit/tag, không chỉ bản cuối.

```python
print(
    git([
        "log",
        "--graph",
        "--decorate",
        "--date=iso-strict",
        "--pretty=format:%h | %ad | %D | %s",
        "--all",
        "-n",
        "80",
    ])
)

print("\nTAGS:")
print(git(["tag", "--sort=creatordate", "-n99"]))
```

Các tag đáng chú ý cần thấy trong lịch sử:

```text
sourceguard-baseline-v1
sourceguard-runtime-index-v1
sourceguard-retrieval-runtime-v1
qg-grounding-governance-v1
qg-pilot-q1-q6-v1
examtrust-project-closure-v1
btc-final-p06-p07-p08-question-v1
```

---

# CELL 07 — KIỂM TRA CÁC COMMIT MỐC CHÍNH

**Mục đích:** show metadata + file list của từng mốc thay vì chỉ tin README.

```python
MILESTONES = {
    "SOURCEGUARD_BASELINE": "73da641e072d5d6a36eb7b986b98432d16e19b9d",
    "PROJECT_CLOSURE": "b0196cdcaf365b808fcb91b1cd85c2e54f4e0903",
    "R2_FINAL_REMOTE_HISTORY": "187b7972348f6279c4ba950577ab4092c4601e97",
    "FINAL_QUESTION_CHECKPOINT": "f56338a14a21e063de3d68eb31c0a6242ad29d18",
    "HISTORY_INTEGRATION": "0e4b3624a3a905ca117918d8609fcb886519fff8",
    "REUSABLE_RAW_PIPELINE": "1d2cabed1e6f669a841399afc92c16f4b13bca0f",
}

for label, commit in MILESTONES.items():
    print("\n" + "="*110)
    print(label, commit)
    print("="*110)
    print(
        git([
            "show",
            "--stat",
            "--summary",
            "--format=FULL SHA: %H%nDATE: %aI%nAUTHOR: %an%nSUBJECT: %s%nPARENTS: %P%n",
            commit,
        ])
    )
```

---

# CELL 08 — VERIFY TAG TARGETS

**Mục đích:** chứng minh tag checkpoint trỏ đúng commit lịch sử.

```python
CHECK_TAGS = [
    "sourceguard-baseline-v1",
    "qg-grounding-governance-v1",
    "qg-pilot-q1-q6-v1",
    "examtrust-project-closure-v1",
    "btc-final-p06-p07-p08-question-v1",
]

for tag in CHECK_TAGS:
    target = git(["rev-parse", tag + "^{}"])
    print(f"{tag:45s} -> {target}")
```

Checkpoint câu hỏi cuối phải trỏ:

```text
btc-final-p06-p07-p08-question-v1
-> f56338a14a21e063de3d68eb31c0a6242ad29d18
```

---

# CELL 09 — LIỆT KÊ ROOT DRIVE BTC

**Mục đích:** xem cấu trúc evidence trên Drive thật.

```python
for p in sorted(BTC_ROOT.iterdir()):
    kind = "DIR " if p.is_dir() else "FILE"
    print(f"{kind}  {p.name}")
```

---

# CELL 10 — SHOW CHECKPOINT P06/P07/P08 TRÊN DRIVE

**Mục đích:** đọc các file index/checkpoint/receipt/replay trực tiếp.

```python
for p in sorted(QUESTION_CP.rglob("*")):
    if p.is_file():
        print(p.relative_to(QUESTION_CP), "|", p.stat().st_size, "bytes")
```

---

# CELL 11 — VERIFY RAW P06/P07/P08 SHA256

**Mục đích:** chứng minh source authority là ảnh RAW gốc.

```python
import hashlib

def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1024*1024), b""):
            h.update(b)
    return h.hexdigest()

RAW = {
    "P06": (
        MYDRIVE / "PILOT01_Physics12_Page06_Source.png",
        "3d524f1df5c37c47754ad08317c6b59c77bb2a77a2598af674b1884389f243c2",
    ),
    "P07": (
        MYDRIVE / "PILOT01_Physics12_Page07_Source.png",
        "081629b1c4973eedf8f7bddc4b2f7f93ff380b1db02ff103c0bf3e2cd6df24ed",
    ),
    "P08": (
        MYDRIVE / "PILOT01_Physics12_Page08_Source.png",
        "59c336d932a0fbe36ad2498f3658724d7d92e176710ac54bdcb2933c93932ac4",
    ),
}

for page, (path, expected) in RAW.items():
    actual = sha256_file(path)
    print(page)
    print(" PATH     =", path)
    print(" EXPECTED =", expected)
    print(" ACTUAL   =", actual)
    print(" RESULT   =", "PASS" if actual == expected else "FAIL")
    print()
```

---

# CELL 12 — HIỂN THỊ ẢNH RAW P06/P07/P08

**Mục đích:** BTC nhìn trực tiếp source page pixels.

```python
from PIL import Image
from IPython.display import display

for page, (path, _) in RAW.items():
    print("\n" + "="*100)
    print(page, path)
    print("="*100)
    display(Image.open(path))
```

---

# CELL 13 — XÁC ĐỊNH EVIDENCE ROOT CỦA FINAL QUESTION

```python
EVID = (
    BTC_ROOT
    / "03_EVIDENCE"
    / "BTC_IMPROVEMENT_MULTI_SOURCE_P06_P07_P08_V1"
)

print("EVIDENCE ROOT =", EVID)
assert EVID.exists()

for p in sorted(EVID.rglob("*")):
    if p.is_file():
        print(p.relative_to(EVID))
```

---

# CELL 14 — SHOW SOURCE UNIT CANDIDATE UNIVERSE

**Mục đích:** show trực tiếp tập Source Unit đã dùng cho quá trình lựa chọn.

```python
import json

def pretty_json(path):
    obj = json.loads(path.read_text(encoding="utf-8"))
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    return obj

p = next(EVID.rglob("BTC_P06_P07_P08_SOURCE_UNIT_CANDIDATE_UNIVERSE_V1.json"))
print("FILE   =", p)
print("SHA256 =", sha256_file(p))
candidate_universe = pretty_json(p)
```

---

# CELL 15 — SHOW HUMAN 3-SOURCE SELECTION

```python
p = next(EVID.rglob("BTC_ADVANCED_HUMAN_3_SOURCE_SELECTION_V1.json"))
print("FILE   =", p)
print("SHA256 =", sha256_file(p))
source_selection = pretty_json(p)
```

Các source cuối cần thấy:

```text
PHY12_P06_R03
PHY12_P07_V01
PHY12_P08_V01
```

---

# CELL 16 — SHOW 3-SOURCE COMPOSITION REVIEW

```python
p = next(EVID.rglob("BTC_ADVANCED_3_SOURCE_COMPOSITION_REVIEW_V1.json"))
print("FILE   =", p)
print("SHA256 =", sha256_file(p))
composition = pretty_json(p)
```

Historical composition SHA đã ghi nhận:

```text
24c28aa0778ae74147769b8ba458d3883e24f65af0650d57edbaca366d9060ae
```

---

# CELL 17 — SHOW QUESTION CONTRACT

```python
p = next(EVID.rglob("BTC_ADVANCED_QUESTION_CONTRACT_V1.json"))
print("FILE   =", p)
print("SHA256 =", sha256_file(p))
contract = pretty_json(p)
```

Historical contract SHA:

```text
0bc489635581413113e579756abcee6874968251c9b982601a03f2631d55ed35
```

---

# CELL 18 — TÌM VÀ SHOW PREGEN PASS

**Mục đích:** tìm đúng artifact có `PASS_FOR_GENERATION` và RL01/RL02/RL03.

```python
PREGEN = None

for p in EVID.rglob("*.json"):
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        continue

    if obj.get("decision") != "PASS_FOR_GENERATION":
        continue

    rels = {
        x.get("relation_id")
        for x in obj.get("relation_ledger", [])
        if isinstance(x, dict)
    }

    if {"RL01","RL02","RL03"}.issubset(rels):
        PREGEN = p
        break

assert PREGEN is not None, "HOLD: không tìm thấy official pregen PASS"

print("FILE   =", PREGEN)
print("SHA256 =", sha256_file(PREGEN))
pregen = pretty_json(PREGEN)
```

BTC cần thấy:

```text
decision = PASS_FOR_GENERATION
RL01
RL02
RL03
```

---

# CELL 19 — SHOW CANDIDATE V1 VÀ POSTGEN V1 FAIL

**Mục đích:** chứng minh hệ thống không che giấu lần sinh chưa đạt.

```python
EXPECTED_V1 = "af504a8336ef754ffa28c7fab0d7fc7d6075572b89e8adbfcf01f87820814dca"
EXPECTED_PG1 = "7460b8f0ea93f0d7a2a1407c5349230712d326055df0a9f64354bb2437bc4d12"

def find_sha(root, expected):
    for p in root.rglob("*"):
        if p.is_file():
            try:
                if sha256_file(p) == expected:
                    return p
            except Exception:
                pass
    return None

v1 = find_sha(EVID, EXPECTED_V1)
pg1 = find_sha(EVID, EXPECTED_PG1)

assert v1 is not None
assert pg1 is not None

print("\nCANDIDATE V1")
print("FILE   =", v1)
print("SHA256 =", sha256_file(v1))
pretty_json(v1)

print("\nPOSTGEN V1")
print("FILE   =", pg1)
print("SHA256 =", sha256_file(pg1))
pretty_json(pg1)
```

BTC cần thấy trạng thái:

```text
Candidate V1 = STRUCTURAL_PASS
Postgen V1   = SOURCE_EVIDENCE_FAIL
Publication  = BLOCKED
```

---

# CELL 20 — SHOW V2 RAW, JSON REPAIR, CANDIDATE V2

```python
names = [
    "BTC_ADVANCED_GENERATION_RAW_V2.txt",
    "BTC_ADVANCED_GENERATION_RAW_V2_JSON_REPAIRED.txt",
    "BTC_ADVANCED_GENERATION_CANDIDATE_V2.json",
]

for name in names:
    p = next(EVID.rglob(name))
    print("\n" + "="*110)
    print("FILE   =", p)
    print("SHA256 =", sha256_file(p))
    print("="*110)
    print(p.read_text(encoding="utf-8"))
```

Historical SHAs:

```text
Raw V2:
91f9603eaf98d926f1102b957301136e878f94464652d5825ecafc65a710b489

Syntax-only repaired:
4d221721b5fce06482b25851034425f5eff03faf90d3e5c021b9f7783ba4ef91

Candidate V2:
7b5a6a69cf0cc56f55584074faec8d2a1cba8df4029a24d94db42f7fbc59b862
```

---

# CELL 21 — SHOW POSTGEN V2 PASS

```python
p = next(EVID.rglob("BTC_ADVANCED_POSTGEN_GROUNDING_V2.json"))
print("FILE   =", p)
print("SHA256 =", sha256_file(p))
postgen_v2 = pretty_json(p)
```

Historical SHA:

```text
f0719db4f4256628fb56a580dddc6000fe713b11d90dbd78ff78e660a21ca669
```

BTC cần thấy:

```text
SOURCE_EVIDENCE_PASS
```

---

# CELL 22 — SHOW FINAL ITEM + TEACHER GATE

```python
p = next(EVID.rglob("BTC_ADVANCED_FINAL_V2.json"))
print("FILE   =", p)
print("SHA256 =", sha256_file(p))
final_item = pretty_json(p)
```

BTC cần thấy:

```text
COGNITIVE = PASS
TEACHER = APPROVED
READY_FOR_USE = TRUE
```

---

# CELL 23 — SHOW FINAL WORKFLOW CHECKPOINT

```python
p = next(EVID.rglob("BTC_FINAL_CHECKPOINT_V2.json"))
print("FILE   =", p)
print("SHA256 =", sha256_file(p))
final_checkpoint = pretty_json(p)
```

BTC cần thấy:

```text
workflow_complete = true
```

---

# CELL 24 — SHOW RETROSPECTIVE CHECKPOINT INDEX

**Mục đích:** phân biệt rõ original historical artifacts và checkpoint/index tạo sau để audit.

```python
for name in [
    "BTC_FINAL_QUESTION_PIPELINE_CHECKPOINT_V1.json",
    "BTC_FINAL_QUESTION_PIPELINE_CHECKPOINT_V1.md",
    "BTC_FINAL_QUESTION_PIPELINE_ARTIFACT_INDEX_V1.csv",
    "BTC_FINAL_QUESTION_PIPELINE_DRIVE_RECEIPT_V1.json",
    "BTC_FINAL_QUESTION_PIPELINE_REPLAY_V1.md",
]:
    hits = list(QUESTION_CP.rglob(name))
    print("\n" + "="*110)
    print(name)
    print("="*110)
    if not hits:
        print("NOT FOUND")
        continue
    p = hits[0]
    print("PATH   =", p)
    print("SHA256 =", sha256_file(p))
    print(p.read_text(encoding="utf-8", errors="replace")[:30000])
```

Checkpoint này phải được hiểu là:

```text
RETROSPECTIVE_INDEX_AND_DURABLE_SNAPSHOT_OF_EXISTING_HISTORY
```

không phải bằng chứng giả tạo rằng checkpoint đã tồn tại tại thời điểm lịch sử gốc.

---

# CELL 25 — SHOW GIT INTEGRATION RECEIPT

```python
p = QUESTION_CP / "BTC_FINAL_QUESTION_PIPELINE_GIT_INTEGRATION_RECEIPT_V1.json"
print("PATH   =", p)
print("SHA256 =", sha256_file(p))
pretty_json(p)
```

Historical receipt SHA đã xác nhận:

```text
47a78e35a9ce5a42df11222a0db16daf8c8d777fcec92ab60a1b05a2d606a979
```

Nó chứng minh merge bảo toàn cả:

```text
f56338a...  final question checkpoint
187b797...  R2 remote history
```

---

# CELL 26 — LOCATE VÀ SHOW REUSABLE PIPELINE SOURCE

**Mục đích:** tránh phụ thuộc việc tên file có được Git hiển thị escape hay không; tìm pipeline theo pattern.

```python
pipeline_hits = list((REPO / "code").glob("examtrust_btc_p06_p07_p08_pipeline_from_raw*.py"))

print("MATCH COUNT =", len(pipeline_hits))
for p in pipeline_hits:
    print("PATH   =", repr(str(p)))
    print("SHA256 =", sha256_file(p))
    print("SIZE   =", p.stat().st_size)

assert len(pipeline_hits) == 1, "HOLD: expected exactly one reusable pipeline"

PIPELINE = pipeline_hits[0]

print("\nFIRST 220 LINES OF PIPELINE:\n")
lines = PIPELINE.read_text(encoding="utf-8").splitlines()
for i, line in enumerate(lines[:220], start=1):
    print(f"{i:04d}: {line}")
```

Expected SHA:

```text
4a2b7a6bf82251ea289139481d1e68c142256a94532d5872733225fea18d3978
```

---

# CELL 27 — SHOW REUSABLE PIPELINE COMMIT

```python
print(
    git([
        "show",
        "--stat",
        "--summary",
        "--format=FULL SHA: %H%nDATE: %aI%nAUTHOR: %an%nSUBJECT: %s%nPARENTS: %P%n",
        "1d2cabed1e6f669a841399afc92c16f4b13bca0f",
    ])
)
```

BTC cần thấy commit message:

```text
feat(btc): add reusable raw-to-ready P06-P07-P08 pipeline
```

---

# CELL 28 — SHOW REUSABLE PIPELINE DRIVE RECEIPT

```python
p = REUSE_CP / "RAW_TO_READY_PIPELINE_GIT_RECEIPT_V1.json"
print("PATH   =", p)
print("SHA256 =", sha256_file(p))
pretty_json(p)
```

Expected SHA:

```text
c8e097d41b348096b774d1346c5dcd5762a73fdd960e17ba4e28d5f18411c6ae
```

---

# CELL 29 — LIỆT KÊ TẤT CẢ REPRODUCIBILITY RUNS

```python
RUN_ROOT = BTC_ROOT / "07_REPRO_RUNS"

runs = sorted(
    [p for p in RUN_ROOT.glob("ET-BTC-RAW-REPLAY-*") if p.is_dir()]
)

print("RUN COUNT =", len(runs))

for p in runs:
    print(p.name)
```

---

# CELL 30 — SHOW LATEST REPRODUCIBILITY RUN

```python
runs = sorted(
    [p for p in RUN_ROOT.glob("ET-BTC-RAW-REPLAY-*") if p.is_dir()],
    key=lambda x: x.stat().st_mtime
)

assert runs, "HOLD: no reproducibility run found"

LATEST_RUN = runs[-1]

print("LATEST RUN =", LATEST_RUN)

for name in [
    "RUN_MANIFEST.json",
    "RUN_REPORT.md",
    "RUN_RECEIPT.json",
]:
    p = LATEST_RUN / name
    print("\n" + "="*110)
    print(name)
    print("="*110)
    print("SHA256 =", sha256_file(p))
    print(p.read_text(encoding="utf-8", errors="replace"))
```

---

# CELL 31 — CHẠY LẠI PIPELINE TỪ RAW

**Mục đích:** chứng minh BTC có thể mở Colab trắng và tái kiểm chứng từ RAW.

```python
import subprocess

run = subprocess.run(
    [
        "python",
        str(PIPELINE),
        "--mode",
        "btc-replay",
    ],
    cwd=str(REPO),
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)

print(run.stdout)
print("EXIT CODE =", run.returncode)

assert run.returncode == 0
assert "RESULT = PASS / RAW_TO_READY_FOR_USE_PIPELINE_VERIFIED" in run.stdout
```

Kết quả cuối phải có:

```text
RAW SOURCE TRUTH ............. PASS
SOURCE UNIT UNIVERSE ......... PASS
HUMAN SOURCE SELECTION ....... PASS
COMPOSITION .................. PASS
QUESTION CONTRACT ............ PASS
PREGEN ....................... PASS_FOR_GENERATION
GENERATION MODE .............. FROZEN_ARTIFACT_REPLAY
CANDIDATE V1 ................. STRUCTURAL_PASS
POSTGEN V1 ................... SOURCE_EVIDENCE_FAIL
CANDIDATE V2 ................. STRUCTURAL_PASS
POSTGEN V2 ................... SOURCE_EVIDENCE_PASS
COGNITIVE .................... PASS
TEACHER ...................... APPROVED
READY_FOR_USE ................ TRUE

RESULT = PASS / RAW_TO_READY_FOR_USE_PIPELINE_VERIFIED
```

---

# CELL 32 — SHOW Q1–Q6 HISTORICAL GIT LINEAGE

**Mục đích:** BTC có thể kiểm tra rằng final demo không phải toàn bộ lịch sử dự án.

```python
print(
    git([
        "log",
        "--date=iso-strict",
        "--pretty=format:%H | %aI | %D | %s",
        "--all",
        "--grep=Q1",
        "--grep=Q2",
        "--grep=Q3",
        "--grep=Q4",
        "--grep=Q5",
        "--grep=Q6",
        "--regexp-ignore-case",
    ])
)
```

Các mốc lịch sử đáng chú ý trong Git gồm Q1/Q2/Q4 accepted/published, Q3 source-insufficiency HOLD, Q5 grounding problem, Q6 source-set HOLD. BTC nên đọc commit/artifact thật thay vì suy ra từ README.

---

# CELL 33 — SHOW PROJECT-CLOSURE HISTORY

```python
print(
    git([
        "show",
        "--stat",
        "--summary",
        "--format=FULL SHA: %H%nDATE: %aI%nAUTHOR: %an%nSUBJECT: %s%nPARENTS: %P%n",
        "b0196cdcaf365b808fcb91b1cd85c2e54f4e0903",
    ])
)

print("\nTAG TARGET:")
print(git(["rev-parse", "examtrust-project-closure-v1^{}"]))
```

---

# CELL 34 — SHOW R2 5-PAGE HISTORY ĐƯỢC MERGE VÀO MAIN

```python
for c in [
    "b7c1fe7175036503aa0e5dc4c801d27858bd4543",
    "9babe35a5635311ad0f568b09d4dc1034e306d72",
    "187b7972348f6279c4ba950577ab4092c4601e97",
]:
    print("\n" + "="*110)
    print(
        git([
            "show",
            "--stat",
            "--summary",
            "--format=FULL SHA: %H%nDATE: %aI%nSUBJECT: %s%nPARENTS: %P%n",
            c,
        ])
    )
```

---

# CELL 35 — SHOW HISTORY-INTEGRATION MERGE

```python
print(
    git([
        "show",
        "--stat",
        "--summary",
        "--format=FULL SHA: %H%nDATE: %aI%nSUBJECT: %s%nPARENTS: %P%n",
        "0e4b3624a3a905ca117918d8609fcb886519fff8",
    ])
)
```

BTC cần thấy merge commit có hai parent:

```text
f56338a14a21e063de3d68eb31c0a6242ad29d18
187b7972348f6279c4ba950577ab4092c4601e97
```

---

# CELL 36 — FINAL MACHINE AUDIT SUMMARY

**Mục đích:** một cell cuối chỉ tổng hợp các authority quan trọng sau khi BTC đã xem chi tiết từng phần.

```python
EXPECTED = {
    "remote_main": "1d2cabed1e6f669a841399afc92c16f4b13bca0f",
    "question_checkpoint": "f56338a14a21e063de3d68eb31c0a6242ad29d18",
    "pipeline_sha": "4a2b7a6bf82251ea289139481d1e68c142256a94532d5872733225fea18d3978",
    "pipeline_receipt_sha": "c8e097d41b348096b774d1346c5dcd5762a73fdd960e17ba4e28d5f18411c6ae",
}

remote = git(["rev-parse", "origin/main"])
tag_target = git(["rev-parse", "btc-final-p06-p07-p08-question-v1^{}"])
pipeline_sha = sha256_file(PIPELINE)
receipt_sha = sha256_file(REUSE_CP / "RAW_TO_READY_PIPELINE_GIT_RECEIPT_V1.json")

checks = {
    "REMOTE MAIN": remote == EXPECTED["remote_main"],
    "QUESTION CHECKPOINT TAG": tag_target == EXPECTED["question_checkpoint"],
    "PIPELINE SHA": pipeline_sha == EXPECTED["pipeline_sha"],
    "PIPELINE RECEIPT SHA": receipt_sha == EXPECTED["pipeline_receipt_sha"],
    "RAW P06": sha256_file(RAW["P06"][0]) == RAW["P06"][1],
    "RAW P07": sha256_file(RAW["P07"][0]) == RAW["P07"][1],
    "RAW P08": sha256_file(RAW["P08"][0]) == RAW["P08"][1],
}

for k, v in checks.items():
    print(f"{k:32s} =", "PASS" if v else "FAIL")

assert all(checks.values()), "HOLD: at least one final authority check failed"

print()
print("RESULT = PASS / BTC_PROJECT_AUTHORITY_VERIFIED")
```

---

# KẾT LUẬN CHO BTC/BGK

Nếu BTC chạy lần lượt các cell trên, họ không cần tin một README tường thuật đơn thuần. Họ có thể tự kiểm tra:

```text
Git history thật
+
Git tags/commits thật
+
Drive RAW thật
+
SHA256 thật
+
historical evidence thật
+
failure lineage V1 thật
+
V2 grounding PASS thật
+
Teacher approval thật
+
checkpoint/receipts thật
+
pipeline .py chạy lại từ RAW thật
```

Điểm cần giữ rõ khi trình bày:

- **Historical original evidence**: artifact sinh ra trong quá trình làm dự án.
- **Historical Git evidence**: commit/tag lưu dấu các mốc thực tế.
- **Retrospective BTC checkpoint/index**: được tạo sau để BTC dễ audit; không giả nhận là artifact lịch sử gốc.
- **Current reproducibility run**: run mới sinh khi BTC chạy pipeline; dùng để chứng minh tính tái kiểm chứng, không phải để thay lịch sử gốc.
