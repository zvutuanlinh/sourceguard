# ============================================================
# EXAMTRUST / SOURCEGUARD — R2 GENERALIZATION RUNNER
# ============================================================
# Prepared for: 8 remaining R2 pages (06,07,11,12,29,39,92,94)
# Base: PAGE08 GOLD (frozen) + PAGE91 (frozen)
#
# HONEST PROVENANCE NOTE (read this before trusting any output):
#
#   VISUAL stage  -> uses sourceguard_engine.py's
#                    visual_ruleset_v2_* functions UNCHANGED.
#                    These are the actual PROMOTED, human-verified
#                    functions (see sourceguard_visual_ruleset_version()
#                    -> "PROMOTED_AFTER_PAGE08_PAGE91_REGRESSION").
#                    This part is the real thing.
#
#   TEXT stage    -> sourceguard_engine.py's grow_regions() was (and
#                    still is) a no-op stub. The Text logic that
#                    produced Page91's frozen result lived only as
#                    ~15 rounds of page-specific manual notebook
#                    patches (V1 -> V1.4 -> rollbacks), which were
#                    NEVER promoted into engine code — confirmed by
#                    RULES/SOURCEGUARD_TEXT_BOX_RULESET_V2_FROZEN.json
#                    itself, whose "not_yet_closed" list literally
#                    says: ["FULL_TEXT_PIPELINE", "ENGINE_PROMOTION", ...].
#                    What IS real and generic is the frozen RULESET
#                    (T01-T15 + EXT01-EXT05, dispatch-by-signal-
#                    priority, "no page-specific coordinates").
#                    The dispatcher below is a FIRST-TIME, faithful
#                    code implementation of that frozen ruleset. It
#                    is new code, not a recovered hidden original.
#
#   LABEL stage   -> same situation: RULES/SOURCEGUARD_LABEL_CONTEXT_
#                    CHAIN_RULESET_V1_FROZEN.json is real and generic
#                    (context inheritance, type codes, display format).
#                    Turning "Bài 21" text into a B21 code, and
#                    deciding CH vs ND vs TN from content, needs a
#                    real classifier; the frozen ruleset defines WHAT
#                    the codes mean, not a trained classifier that
#                    guesses them from pixels. The heuristic below is
#                    a first pass and WILL make mistakes — every box
#                    it produces is written with a confidence flag so
#                    you can see exactly which ones to check by eye,
#                    the same way every stage in this project always
#                    ended in "HUMAN REVIEW" before being frozen.
#
# This script does NOT claim Page-8-final-clean quality out of the
# box. Page 8 reached that quality after ~30 rounds of human-in-the-
# loop patching (see HISTORY/PIPELINE_PAGE91.json cells 59-89). What
# this script gives you is the same first-pass -> HOLD-flagged draft
# -> you review -> promote workflow the project has always used,
# just automated as far as it can honestly be automated today.
# ============================================================

import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

import cv2
import numpy as np

try:
    import pytesseract
    _HAS_OCR = True
except Exception:
    _HAS_OCR = False

import sourceguard_engine as sg


# ============================================================
# 0. Shared helpers
# ============================================================

def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def union_box(boxes):
    xs1 = [b[0] for b in boxes]
    ys1 = [b[1] for b in boxes]
    xs2 = [b[2] for b in boxes]
    ys2 = [b[3] for b in boxes]
    return [min(xs1), min(ys1), max(xs2), max(ys2)]


def boxes_intersect(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    return (ix2 - ix1) * (iy2 - iy1)


def bbox_area(b):
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


# ============================================================
# 1. RAW VISUAL CANDIDATE PROPOSAL (generic, source-adaptive)
#
# Rebuilt from the exported CELL_102 module (visual_functions.zip).
# The exported zip did not include the exact original threshold
# constants (only the algorithm shape: edge-density -> Otsu ->
# morphological close/dilate -> contour boxes -> merge -> filter).
# The constants below are reasonable generic defaults, NOT the
# original secret numbers. Downstream validate_objects() /
# visual_ruleset_v2_* (which ARE the original promoted logic) do
# the real precision filtering, so this stage is deliberately
# high-recall / low-precision by design (same as the project's own
# "raw_proposals: 5 -> validation_true: 3" pattern on Page91).
# ============================================================

CLOSE_KERNEL_RATIO = 0.006
DILATE_KERNEL_RATIO = 0.003
MIN_AREA_RATIO = 0.004
MIN_WIDTH_RATIO = 0.05
MIN_HEIGHT_RATIO = 0.02
MAX_ASPECT_RATIO = 6.0
MAX_AREA_RATIO = 0.32          # generic sanity cap: reject implausible
                                # whole-page "visual" blobs (textbook
                                # pages here never have an illustration
                                # covering this much of the page) -- not
                                # in the original export, added because
                                # the reconstructed constants above are
                                # not the original secret thresholds
MERGE_DISTANCE_PX_RATIO = 0.008


def _odd(v):
    v = int(round(v))
    return v if v % 2 == 1 else v + 1


def compute_edge_density_map(gray):
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    gx = cv2.Sobel(blurred, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(blurred, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)
    mag = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
    return mag.astype(np.uint8)


def compute_binary_structure_mask(gray, page_w):
    edge_map = compute_edge_density_map(gray)
    _, binary = cv2.threshold(edge_map, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    close_k = _odd(page_w * CLOSE_KERNEL_RATIO)
    dilate_k = _odd(page_w * DILATE_KERNEL_RATIO)
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (close_k, close_k))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, close_kernel, iterations=2)
    dilate_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (dilate_k, dilate_k))
    dilated = cv2.dilate(closed, dilate_kernel, iterations=1)
    return dilated, edge_map


def extract_candidate_boxes(mask, page_w, page_h):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    page_area = float(page_w * page_h)
    min_area = MIN_AREA_RATIO * page_area
    min_w = MIN_WIDTH_RATIO * page_w
    min_h = MIN_HEIGHT_RATIO * page_h
    boxes = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        area = w * h
        if area < min_area or w < min_w or h < min_h:
            continue
        aspect = max(w, h) / float(min(w, h))
        if aspect > MAX_ASPECT_RATIO:
            continue
        if area > MAX_AREA_RATIO * page_area:
            continue
        boxes.append([x, y, x + w, y + h])
    return boxes


def _boxes_should_merge(a, b, gap_px):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    dx = max(0, max(ax1, bx1) - min(ax2, bx2))
    dy = max(0, max(ay1, by1) - min(ay2, by2))
    return dx <= gap_px and dy <= gap_px


def merge_boxes(boxes, page_w, gap_px=None):
    n = len(boxes)
    if n == 0:
        return []
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    if gap_px is None:
        gap_px = MERGE_DISTANCE_PX_RATIO * page_w
    for i in range(n):
        for j in range(i + 1, n):
            if _boxes_should_merge(boxes[i], boxes[j], gap_px):
                union(i, j)

    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(boxes[i])

    return [union_box(g) for g in groups.values()]


def decompose_oversized_region(image_bgr, box, page_w, page_h):
    """
    Family B fix (Joule/P12 miss): a raw contour that exceeds
    MAX_AREA_RATIO was previously just discarded outright, so a large
    mixed region (apparatus drawing + surrounding text/whitespace)
    lost its visual proposal entirely -- confirmed root-cause chain in
    the debug dossier: compute_binary_structure_mask -> RETR_EXTERNAL
    (parent-only) -> MAX_AREA rejection -> no independent proposal.

    This is a local decomposition INSIDE discovery (SG-VIS-007: "...
    without creating a new processing stage"), not a page-specific
    rescue: crop the oversized region, re-run structure detection with
    RETR_TREE (keeps nested/internal contours that RETR_EXTERNAL
    discards) and a much smaller merge distance, so a drawing embedded
    inside a bigger mixed blob can surface as its own child candidate.
    """
    x1, y1, x2, y2 = [int(v) for v in box]
    sub = image_bgr[y1:y2, x1:x2]
    if sub.size == 0:
        return []
    sub_h, sub_w = sub.shape[:2]
    gray = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
    edge_map = compute_edge_density_map(gray)
    _, binary = cv2.threshold(edge_map, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    close_k = _odd(max(3, sub_w * 0.02))
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (close_k, close_k))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, close_kernel, iterations=1)

    contours, _ = cv2.findContours(closed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    page_area = float(page_w * page_h)
    min_area = MIN_AREA_RATIO * page_area
    min_w = MIN_WIDTH_RATIO * page_w * 0.6   # slightly relaxed: children are sub-parts
    min_h = MIN_HEIGHT_RATIO * page_h * 0.6

    children = []
    for c in contours:
        cx, cy, cw, ch = cv2.boundingRect(c)
        area = cw * ch
        if area < min_area or cw < min_w or ch < min_h:
            continue
        if area > 0.9 * sub_w * sub_h:  # basically the whole crop again -> not a real child
            continue
        # HARD SAFETY CAP (bug fix: P39 showed a child that survived the
        # 0.9*sub-crop check but still covered 88% of the WHOLE PAGE,
        # because the sub-crop itself was already most of the page).
        # A single visual is never allowed to exceed MAX_AREA_RATIO of
        # the page, full stop -- no further recursive decomposition is
        # attempted (the dossier already established that a same-
        # detector rescan does not reliably split these further).
        if area > MAX_AREA_RATIO * page_area:
            continue
        children.append([x1 + cx, y1 + cy, x1 + cx + cw, y1 + cy + ch])

    if not children:
        return []

    # tight merge only (avoid re-collapsing back into one giant blob)
    tight_gap = max(2, int(0.01 * page_w))
    merged = merge_boxes(children, page_w, gap_px=tight_gap)
    return merged if merged else children


def raw_visual_candidates(image_bgr):
    """Generic high-recall visual-object proposal. Output: list[[x1,y1,x2,y2]]."""
    page_h, page_w = image_bgr.shape[:2]
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    mask, _ = compute_binary_structure_mask(gray, page_w)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    page_area = float(page_w * page_h)
    min_area = MIN_AREA_RATIO * page_area
    min_w = MIN_WIDTH_RATIO * page_w
    min_h = MIN_HEIGHT_RATIO * page_h

    boxes = []
    oversized = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        area = w * h
        if area < min_area or w < min_w or h < min_h:
            continue
        aspect = max(w, h) / float(min(w, h))
        if aspect > MAX_ASPECT_RATIO:
            continue
        if area > MAX_AREA_RATIO * page_area:
            oversized.append([x, y, x + w, y + h])
            continue
        boxes.append([x, y, x + w, y + h])

    # normal boxes get the usual loose merge (join nearby fragments of
    # the same figure) -- done BEFORE mixing in decomposed children.
    boxes = merge_boxes(boxes, page_w)

    # BUG FIX (found via P39: one merged box covered 88% of the page).
    # MAX_AREA_RATIO was only checked on individual raw contours BEFORE
    # merge_boxes(). merge_boxes() unions transitively (union-find), so
    # a page with many scattered structure fragments within gap_px of
    # each other can chain-merge into one page-spanning blob even
    # though no single original contour was oversized. Re-check AFTER
    # merge and send anything still oversized through the same
    # decomposition path as before.
    still_ok = []
    for b in boxes:
        if bbox_area(b) > MAX_AREA_RATIO * page_area:
            oversized.append(b)
        else:
            still_ok.append(b)
    boxes = still_ok

    # Family B fix: don't just drop oversized regions -- try to recover
    # independent child visuals from inside them. Decomposed children
    # are already tightly merged among themselves inside
    # decompose_oversized_region() and must NOT go through the loose
    # page-level merge again below, or they collapse straight back into
    # one oversized blob (this was verified happening on P12: the
    # correct decomposition was found, then silently re-merged away).
    decomposed_children = []
    for ob in oversized:
        decomposed_children.extend(decompose_oversized_region(image_bgr, ob, page_w, page_h))

    boxes = boxes + decomposed_children
    boxes = _dedupe_by_iou(boxes)
    boxes.sort(key=lambda b: (b[1], b[0]))
    return boxes


def _dedupe_by_iou(boxes, iou_thresh=0.6):
    """Drop near-duplicate boxes (RETR_TREE can yield an inner+outer
    contour pair for the same shape; decomposition can also rediscover
    a box already found by the normal pass). Keeps the larger box."""
    boxes = sorted(boxes, key=lambda b: -bbox_area(b))
    kept = []
    for b in boxes:
        dup = False
        for k in kept:
            inter = boxes_intersect(b, k)
            union_area = bbox_area(b) + bbox_area(k) - inter
            iou = inter / union_area if union_area > 0 else 0
            if iou >= iou_thresh:
                dup = True
                break
        if not dup:
            kept.append(b)
    return kept


# ============================================================
# 2. PHYSICAL TEXT LINES (adapted from visual_functions/CELL_085
#    extract_whole_lines — this one WAS present complete in the
#    export, kept close to verbatim; only renamed locals for clarity)
# ============================================================

def extract_whole_lines(page_bgr, exclusions):
    ph, pw = page_bgr.shape[:2]
    gray = cv2.cvtColor(page_bgr, cv2.COLOR_BGR2GRAY)
    mask = np.ones((ph, pw), dtype=np.uint8) * 255

    for box in exclusions:
        x1, y1, x2, y2 = [int(v) for v in box]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(pw, x2), min(ph, y2)
        if x2 > x1 and y2 > y1:
            mask[y1:y2, x1:x2] = 0

    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 15
    )
    binary[mask == 0] = 0

    count, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)

    comps = []
    for i in range(1, count):
        x = int(stats[i, cv2.CC_STAT_LEFT])
        y = int(stats[i, cv2.CC_STAT_TOP])
        cw = int(stats[i, cv2.CC_STAT_WIDTH])
        ch = int(stats[i, cv2.CC_STAT_HEIGHT])
        ca = int(stats[i, cv2.CC_STAT_AREA])
        if 2 <= ch <= ph * 0.055 and 1 <= cw <= pw * 0.10 and ca >= 2:
            comps.append({"bbox": [x, y, x + cw, y + ch],
                          "cx": float(centroids[i][0]), "cy": float(centroids[i][1])})

    if len(comps) < 10:
        return {"whole_lines": [], "glyph_h_med": 1.0}

    heights = [c["bbox"][3] - c["bbox"][1] for c in comps]
    glyph_h_med = float(np.median(heights))
    baseline_tol = max(2.0, glyph_h_med * 0.70)

    rows = []
    for comp in sorted(comps, key=lambda c: (c["cy"], c["cx"])):
        best_idx, best_dist = None, None
        for idx, row in enumerate(rows):
            d = abs(comp["cy"] - row["center_y"])
            if d <= baseline_tol and (best_dist is None or d < best_dist):
                best_idx, best_dist = idx, d
        if best_idx is None:
            rows.append({"components": [comp], "center_y": comp["cy"]})
        else:
            rows[best_idx]["components"].append(comp)
            rows[best_idx]["center_y"] = float(
                np.median([c["cy"] for c in rows[best_idx]["components"]])
            )

    whole_lines = []
    for row in rows:
        row_comps = sorted(row["components"], key=lambda c: c["bbox"][0])
        if len(row_comps) < 2:
            continue

        gaps = [b["bbox"][0] - a["bbox"][2] for a, b in zip(row_comps[:-1], row_comps[1:])]
        positive_gaps = [g for g in gaps if g >= 0]
        normal_gap = float(np.median(positive_gaps)) if positive_gaps else 0.0

        groups = [[row_comps[0]]]
        for prev, cur in zip(row_comps[:-1], row_comps[1:]):
            gap = cur["bbox"][0] - prev["bbox"][2]
            split_gap = gap > normal_gap + glyph_h_med * 3.0
            if split_gap:
                groups.append([cur])
            else:
                groups[-1].append(cur)

        for group in groups:
            if len(group) < 2:
                continue
            box = union_box([c["bbox"] for c in group])
            if any(boxes_intersect(box, ex) > 0 for ex in exclusions):
                continue
            x1, y1, x2, y2 = box
            whole_lines.append({
                "bbox": [x1, y1, x2, y2],
                "left": x1, "right": x2, "width": x2 - x1, "height": y2 - y1,
                "component_count": len(group),
                "baseline_y": float(row["center_y"]),
            })

    whole_lines.sort(key=lambda r: (r["bbox"][1], r["bbox"][0]))
    return {"whole_lines": whole_lines, "glyph_h_med": glyph_h_med}


def text_overlap_ratio(box, whole_lines):
    area = bbox_area(box)
    if area <= 0:
        return 0.0
    covered = sum(boxes_intersect(box, ln["bbox"]) for ln in whole_lines)
    return min(1.0, covered / area)


# ============================================================
# 3. VISUAL STAGE — uses the real, promoted engine functions
#    Architecture: Container -> Object -> Validation -> Visual V2
# ============================================================

import statistics


def _paragraph_geometry_signal(box, whole_lines):
    """
    Family A fix (per debug dossier): engine._visual_validation_decision
    only rejects a text-dominant candidate when
    (aspect_ratio>=4 AND text_overlap>=0.45) or a tiny fragment -- so a
    roughly square/tall paragraph block (very common: normal body text)
    slips through as KEEP_VISUAL. _sgv2_is_paragraph_like() in the
    engine can't help either, since extract_whole_lines() never
    populates a "text" field for it to read (confirmed: len(words) is
    always 0 for this producer's data).

    This is a supplemental, generic (no page coordinates) geometric
    paragraph detector added in the PRODUCER, not in the frozen engine:
    a block containing >=3 stacked whole_lines that are consistently
    left-aligned relative to the block width, with material text
    coverage, is almost certainly a paragraph -- independent of aspect
    ratio. Returns (is_paragraph_like, evidence_dict).
    """
    bx1, by1, bx2, by2 = box
    bw = max(1.0, bx2 - bx1)
    inside = []
    for ln in whole_lines:
        lb = ln["bbox"]
        inter = boxes_intersect(box, lb)
        line_area = bbox_area(lb)
        if line_area > 0 and inter / line_area >= 0.7:
            inside.append(ln)

    overlap = text_overlap_ratio(box, whole_lines)

    if len(inside) < 3:
        return False, {"lines_inside": len(inside), "text_overlap": overlap}

    lefts = [ln["bbox"][0] for ln in inside]
    left_std_ratio = (statistics.pstdev(lefts) / bw) if len(lefts) > 1 else 0.0

    # FILES3 P06 DIRECT FIX V2
    #
    # whole-line overlap alone cannot prove paragraph semantics:
    # labels/symbols inside a diagram can produce high overlap.
    #
    # Narrow protection:
    #   - several internal lines
    #   - high overlap
    #   - visibly non-uniform left structure
    #   - compact/medium candidate
    #
    # This ONLY allows the candidate to reach the existing
    # SourceGuard validator. It does not itself promote VISUAL.
    bh = max(1.0, by2 - by1)
    aspect_wh = bw / bh

    mixed_visual_protect = (
        3 <= len(inside) <= 12
        and overlap >= 0.55
        and 0.15 <= left_std_ratio < 0.20
        and 0.90 <= aspect_wh <= 1.45
    )

    is_paragraph = (
        (
            (left_std_ratio < 0.15 and overlap >= 0.25)
            or (overlap >= 0.30)
        )
        and not mixed_visual_protect
    )

    return is_paragraph, {
        "lines_inside": len(inside),
        "left_std_ratio": round(left_std_ratio, 3),
        "text_overlap": round(overlap, 3),
    }



# ================================================================================================
# P07 CUMULATIVE FAMILY — GENERIC MULTI-PANEL VISUAL RECONSTRUCTION
# ================================================================================================

def files3_horizontal_sibling_signature(box, other_box, page_w, page_h):
    """
    Generic geometry test for two side-by-side panels.

    No page ID.
    No absolute coordinates.
    """

    ax1,ay1,ax2,ay2 = map(float, box)
    bx1,by1,bx2,by2 = map(float, other_box)

    aw=max(1.0,ax2-ax1)
    ah=max(1.0,ay2-ay1)
    bw=max(1.0,bx2-bx1)
    bh=max(1.0,by2-by1)

    cy_a=(ay1+ay2)/2.0
    cy_b=(by1+by2)/2.0

    height_ratio=min(ah,bh)/max(ah,bh)
    width_ratio=min(aw,bw)/max(aw,bw)

    center_delta=abs(cy_a-cy_b)/max(ah,bh)

    if bx1 >= ax2:
        gap=bx1-ax2
    elif ax1 >= bx2:
        gap=ax1-bx2
    else:
        gap=0.0

    gap_ratio=gap/max(aw,bw)

    return (
        height_ratio >= 0.82
        and width_ratio >= 0.78
        and center_delta <= 0.12
        and gap_ratio <= 0.20
    )


def files3_find_horizontal_sibling_rows(raw_boxes, page_w, page_h):
    """
    Find >=3 strongly aligned, similarly sized, side-by-side
    visual proposals.

    This stage only produces evidence.
    """

    boxes=[list(map(int,b)) for b in raw_boxes]

    rows=[]

    for i,a in enumerate(boxes):

        members=[a]

        for j,b in enumerate(boxes):

            if i == j:
                continue

            if files3_horizontal_sibling_signature(
                a,b,page_w,page_h
            ):
                members.append(b)

        # dedupe
        unique=[]

        for b in members:
            if b not in unique:
                unique.append(b)

        unique.sort(key=lambda b:b[0])

        if len(unique) < 3:
            continue

        # Require genuinely horizontal spread.
        row_union=union_box(unique)

        rw=row_union[2]-row_union[0]
        rh=max(1,row_union[3]-row_union[1])

        if rw/rh < 3.5:
            continue

        # Prevent huge page-level structures.
        if rw/page_w > 0.88:
            continue

        key=tuple(tuple(x) for x in unique)

        if not any(
            tuple(tuple(x) for x in r) == key
            for r in rows
        ):
            rows.append(unique)

    return rows


def files3_sibling_rescue_set(raw_boxes, whole_lines, page_w, page_h):
    """
    Rescue paragraph-prefilter candidates only when they are members
    of a strong >=3 horizontal sibling row.

    Important:
      This does NOT validate/promote the object.
      It only allows it to reach existing SourceGuard validation.
    """

    rows=files3_find_horizontal_sibling_rows(
        raw_boxes,page_w,page_h
    )

    rescue=set()

    for row in rows:

        # At least one member must already look non-paragraph-like
        # under the existing accepted detector. This anchors the row
        # to an independently surviving visual candidate.
        natural_survivors=0

        for b in row:
            is_para,_=_paragraph_geometry_signal(
                b,whole_lines
            )

            if not is_para:
                natural_survivors += 1

        if natural_survivors < 1:
            continue

        for b in row:
            rescue.add(tuple(map(int,b)))

    return rescue,rows


def files3_line_horizontal_overlap(line_box, group_box):
    lx1,ly1,lx2,ly2=map(float,line_box)
    gx1,gy1,gx2,gy2=map(float,group_box)

    inter=max(
        0.0,
        min(lx2,gx2)-max(lx1,gx1)
    )

    lw=max(1.0,lx2-lx1)

    return inter/lw


def files3_build_visual_composites(
    visuals,
    base_lines,
    sibling_rows,
    page_w,
    page_h
):
    """
    Promote a sibling row to one COMPOSITE_VISUAL when:

      1. >=3 actual final visual children correspond to the sibling row.
      2. A short local-label line exists immediately below each child.
      3. A shared caption spans the sibling group below local labels.
      4. Caption growth stops on a geometric left reset / body-text start.

    No OCR semantics required.
    No page ID.
    No absolute coordinates.
    """

    if not visuals or not sibling_rows:
        return visuals,[]

    remaining=list(visuals)
    composites=[]

    for row in sibling_rows:

        row=[list(map(int,b)) for b in row]
        row.sort(key=lambda b:b[0])

        matched=[]

        for rb in row:

            best=None
            best_score=0.0

            for v in remaining:

                cb=list(map(int,v["core_bbox"]))

                ix=max(
                    0,
                    min(rb[2],cb[2])-max(rb[0],cb[0])
                )

                iy=max(
                    0,
                    min(rb[3],cb[3])-max(rb[1],cb[1])
                )

                inter=ix*iy

                ra=max(
                    1,
                    (rb[2]-rb[0])*(rb[3]-rb[1])
                )

                ca=max(
                    1,
                    (cb[2]-cb[0])*(cb[3]-cb[1])
                )

                score=inter/min(ra,ca)

                if score > best_score:
                    best_score=score
                    best=v

            if best is not None and best_score >= 0.80:
                if best not in matched:
                    matched.append(best)

        if len(matched) < 3:
            continue

        matched.sort(
            key=lambda v:v["core_bbox"][0]
        )

        child_boxes=[
            list(map(int,v["core_bbox"]))
            for v in matched
        ]

        group_core=union_box(child_boxes)

        gx1,gy1,gx2,gy2=group_core

        child_heights=[
            b[3]-b[1]
            for b in child_boxes
        ]

        med_h=float(
            np.median(child_heights)
        )

        # ------------------------------------------------------------
        # LOCAL LABELS
        # ------------------------------------------------------------

        local_labels=[]

        for child in child_boxes:

            cx1,cy1,cx2,cy2=child

            candidates=[]

            for ln in base_lines:

                lb=ln["bbox"]
                lx1,ly1,lx2,ly2=lb

                gap=ly1-cy2

                if gap < 0:
                    continue

                if gap > max(
                    0.22*med_h,
                    page_h*0.025
                ):
                    continue

                center=(lx1+lx2)/2.0

                if not (
                    cx1 <= center <= cx2
                ):
                    continue

                width=lx2-lx1

                if width > (
                    cx2-cx1
                )*0.45:
                    continue

                candidates.append(
                    (gap,width,ln)
                )

            if not candidates:
                local_labels=[]
                break

            candidates.sort(
                key=lambda x:(x[0],x[1])
            )

            local_labels.append(
                candidates[0][2]
            )

        if len(local_labels) != len(child_boxes):
            continue

        label_bottom=max(
            ln["bbox"][3]
            for ln in local_labels
        )

        # ------------------------------------------------------------
        # SHARED CAPTION
        # ------------------------------------------------------------

        possible=[]

        for ln in base_lines:

            lb=ln["bbox"]
            lx1,ly1,lx2,ly2=lb

            if ly1 <= label_bottom:
                continue

            gap=ly1-label_bottom

            if gap > max(
                page_h*0.065,
                med_h*0.70
            ):
                continue

            overlap=files3_line_horizontal_overlap(
                lb,
                group_core
            )

            width_ratio=(
                (lx2-lx1)
                / max(1.0,gx2-gx1)
            )

            if (
                overlap >= 0.85
                and width_ratio >= 0.35
            ):
                possible.append(ln)

        possible.sort(
            key=lambda x:x["bbox"][1]
        )

        if not possible:
            continue

        caption=[]

        previous_bottom=label_bottom

        caption_left=None

        stop_reason=None
        stop_evidence=None

        for ln in possible:

            b=ln["bbox"]

            gap=b[1]-previous_bottom

            if gap > max(
                page_h*0.025,
                med_h*0.28
            ):
                if caption:
                    break

            # After caption has started, a strong reset to the left
            # with a meaningful-width line is treated as a new body
            # block rather than caption continuation.
            if caption:

                current_left=b[0]

                reset=(
                    caption_left-current_left
                )

                meaningful_width=(
                    (b[2]-b[0])
                    >= (gx2-gx1)*0.45
                )

                if (
                    reset
                    >= (gx2-gx1)*0.12
                    and meaningful_width
                ):

                    stop_reason=(
                        "GEOMETRIC_NEW_TEXT_BLOCK"
                    )

                    stop_evidence={
                        "stop_bbox":
                            list(map(int,b)),

                        "caption_left":
                            int(caption_left),

                        "current_left":
                            int(current_left),

                        "reset_px":
                            int(reset),

                        "group_width":
                            int(gx2-gx1),

                        "meaningful_width":
                            True
                    }

                    break

            caption.append(ln)

            if caption_left is None:
                caption_left=b[0]
            else:
                caption_left=min(
                    caption_left,b[0]
                )

            previous_bottom=b[3]

        if not caption:
            continue

        # Caption should materially span the whole sibling group.
        caption_union=union_box(
            [x["bbox"] for x in caption]
        )

        caption_span_ratio=(
            (caption_union[2]-caption_union[0])
            / max(1.0,gx2-gx1)
        )

        if caption_span_ratio < 0.55:
            continue

        composite_box=union_box(
            child_boxes
            + [x["bbox"] for x in local_labels]
            + [x["bbox"] for x in caption]
        )

        confidence=max(
            float(v.get("confidence",0.0))
            for v in matched
        )

        composite={
            "core_bbox":
                group_core,

            "full_bbox":
                composite_box,

            "caption_lines":
                len(caption),

            "grow_full_object_bbox_FYI_NOT_USED":
                None,

            "confidence":
                confidence,

            "semantic_role":
                "COMPOSITE_VISUAL",

            "composite_type":
                "SIBLING_VISUALS_SHARED_CAPTION",

            "children_visuals":
                child_boxes,

            "local_labels":
                [
                    list(map(int,x["bbox"]))
                    for x in local_labels
                ],

            "shared_caption_lines":
                [
                    list(map(int,x["bbox"]))
                    for x in caption
                ],

            "shared_caption_bbox":
                list(map(int,caption_union)),

            "caption_span_ratio":
                float(caption_span_ratio),

            "promotion_rule":
                "SIBLING_VISUALS+SHARED_CAPTION",

            "stop_reason":
                stop_reason,

            "stop_evidence":
                stop_evidence
        }

        composites.append(composite)

        remaining=[
            v
            for v in remaining
            if v not in matched
        ]

    final_visuals=remaining+composites

    final_visuals.sort(
        key=lambda v:(
            v["full_bbox"][1],
            v["full_bbox"][0]
        )
    )

    return final_visuals,composites




def run_visual_stage(image_bgr, container):
    page_w, page_h = container["width"], container["height"]

    raw_boxes = raw_visual_candidates(image_bgr)
    # text_items needed for evidence + local_grow/caption_chain use the
    # SAME whole-line extractor as the Text stage, run with no exclusions yet.
    base_lines = extract_whole_lines(image_bgr, exclusions=[])["whole_lines"]

    # Family A supplemental pre-filter: drop paragraph-like blocks
    # BEFORE they ever reach create_objects/validate_objects, since the
    # engine's own narrow aspect-gated rule lets them through.
    # P07 cumulative generic sibling rescue.
    # Strong horizontal sibling geometry can protect a candidate from
    # paragraph PREFILTER only. Existing SourceGuard validation still
    # decides whether it becomes a validated visual.
    sibling_rescue_set, sibling_rows = files3_sibling_rescue_set(
        raw_boxes,
        base_lines,
        page_w,
        page_h
    )

    supplemental_rejected = []
    sibling_rescued = []
    filtered_boxes = []

    for b in raw_boxes:
        is_para, ev = _paragraph_geometry_signal(b, base_lines)

        protected = tuple(map(int,b)) in sibling_rescue_set

        if is_para and not protected:
            supplemental_rejected.append({
                "bbox": b,
                "evidence": ev
            })
        else:
            filtered_boxes.append(b)

            if is_para and protected:
                sibling_rescued.append({
                    "bbox": list(map(int,b)),
                    "evidence": ev,
                    "reason": "HORIZONTAL_SIBLING_ROW"
                })

    raw_boxes = filtered_boxes

    candidates = []
    for b in raw_boxes:
        overlap = text_overlap_ratio(b, base_lines)
        candidates.append({
            "type": "VISUAL",
            "bbox": b,
            "confidence": 1.0 - overlap,
            "evidence": {"text_overlap": overlap},
        })

    objects = sg.create_objects(candidates)
    objects = sg.validate_objects(objects, container=container)

    validated = [o for o in objects if o.status.value == "VALIDATED"]

    # sibling grouping (does not alter geometry)
    groups = sg.visual_ruleset_v2_group_candidates(validated)

    verified_visuals = []
    sibling_boxes_all = [list(map(int, o.core_bbox)) for o in validated]

    for obj in validated:
        core = list(map(int, obj.core_bbox))
        local_lines = [ln for ln in base_lines
                       if boxes_intersect(core, ln["bbox"]) == 0]  # exclude self-overlap noise
        siblings = [b for b in sibling_boxes_all if b != core]

        # NOTE (fix, per debug dossier "loi_cua_code_claude.pdf"):
        # engine.visual_ruleset_v2_caption_chain() returns a LIST of
        # attached caption-line dicts (`return attached`), NOT a dict.
        # engine.visual_ruleset_v2_local_grow() returns a dict whose key
        # is "full_object_bbox", NOT "full_bbox". The previous code read
        # the wrong shapes for both, so caption_lines was always 0 and
        # full_bbox always equalled core_bbox for all 17 visuals.
        #
        # We call local_grow() only to keep it available for inspection/
        # regression, but per the dossier's own runtime evidence we do
        # NOT adopt its full_object_bbox as the final box: on P07_R02,
        # P94_R04 (and P11_R01, already-correct) it can swallow sibling
        # paragraphs or over-grow an already-correct core. We use ONLY
        # the caption_chain() list, unioned with the core -- this was
        # verified safe across all 7 known CAPTION_MISSING cases.
        grown = sg.visual_ruleset_v2_local_grow(
            core, local_lines, page_w, page_h,
            sibling_core_bboxes=siblings,
        )
        caption = sg.visual_ruleset_v2_caption_chain(core, local_lines, page_w, page_h)

        full_box = core
        caption_lines = 0
        try:
            if isinstance(caption, list) and caption:
                caption_lines = len(caption)
                cap_boxes = [list(map(int, c["bbox"])) for c in caption if c.get("bbox")]
                if cap_boxes:
                    full_box = union_box([core] + cap_boxes)
        except Exception:
            pass

        grow_full_object_bbox = None
        try:
            if isinstance(grown, dict) and grown.get("full_object_bbox"):
                grow_full_object_bbox = list(map(int, grown["full_object_bbox"]))
        except Exception:
            pass

        verified_visuals.append({
            "core_bbox": core,
            "full_bbox": full_box,
            "caption_lines": caption_lines,
            "grow_full_object_bbox_FYI_NOT_USED": grow_full_object_bbox,
            "confidence": obj.confidence,
        })

    # Generic sibling + local-label + shared-caption composite stage.
    verified_visuals, composites = files3_build_visual_composites(
        verified_visuals,
        base_lines,
        sibling_rows,
        page_w,
        page_h
    )

    return {
        "raw_proposals": len(raw_boxes),
        "validated": len(verified_visuals),
        "rejected": len(objects) - len([
            o for o in objects
            if o.status.value == "VALIDATED"
        ]),
        "supplemental_paragraph_rejected": supplemental_rejected,
        "sibling_rescued": sibling_rescued,
        "sibling_rows": sibling_rows,
        "groups": len(groups) if groups else 0,
        "composites": composites,
        "visuals": verified_visuals,
    }


# ============================================================
# 4. TEXT STAGE — first-time implementation of the FROZEN
#    SOURCEGUARD_TEXT_BOX_RULESET_V2 (T01-T15, EXT01-EXT05)
# ============================================================

import re

_STRUCTURAL_START_RE = re.compile(
    r"^\s*("
    r"[IVXLC]+\s*[\.\)]\s+[A-ZĐÀÁẢÃẠÂẦẤẨẪẬĂẰẮẲẴẶÊỀẾỂỄỆÔỒỐỔỖỘƠỜỚỞỠỢƯỪỨỬỮỰ]"  # roman heading: "I. MÔ HÌNH..."
    r"|CH(Ư|U)ƠNG\b"
    r"|B(À|A)I\s+\d+\b"
    r")",
    re.IGNORECASE,
)

# NOTE (fix, per contact-sheet + gold comparison): plain enumeration
# markers ("1.", "2.", "a)", "b)") are body-level list items, not
# region/heading boundaries -- Page08 GOLD groups a whole numbered
# exercise ("1. ... 2. ...") into ONE region, not one region per
# number. The previous version's structural-start regex matched these
# too, which combined with LANE_CHANGE below produced ~40 one-line
# regions per page instead of ~8-10 content-level regions.


def _classify_line_signal(ocr_text):
    """T01/T02: is this line strong evidence of a new SECTION/CHAPTER/
    LESSON heading (not a body-level enumeration marker)."""
    t = (ocr_text or "").strip()
    if not t:
        return False
    return bool(_STRUCTURAL_START_RE.match(t))


def _ocr_line_text(image_bgr, box):
    if not _HAS_OCR:
        return ""
    x1, y1, x2, y2 = [max(0, int(v)) for v in box]
    crop = image_bgr[y1:y2, x1:x2]
    if crop.size == 0:
        return ""
    try:
        return pytesseract.image_to_string(crop, lang="vie", config="--psm 7").strip()
    except Exception:
        try:
            return pytesseract.image_to_string(crop, config="--psm 7").strip()
        except Exception:
            return ""


def _split_into_column_bands(lines, page_w):
    """
    Fix for the LANE_CHANGE fragmentation bug: a page with a sidebar
    ("EM CÓ BIẾT" box, a note panel, etc.) has lines from two physical
    reading columns. Sorting all lines by y alone interleaves the two
    columns, so the old single-pass scan saw the left-x jump on almost
    every line and flushed a new 1-line region each time.

    Cluster lines into column bands by left-x (gap-based 1D
    clustering), then the caller processes each band top-to-bottom
    independently, so a column's own paragraphs stay contiguous.
    Bands are returned left-to-right.
    """
    if not lines:
        return []
    xs = sorted(set(ln["bbox"][0] for ln in lines))
    gap_thresh = page_w * 0.12
    bands_x = [[xs[0]]]
    for x in xs[1:]:
        if x - bands_x[-1][-1] > gap_thresh:
            bands_x.append([x])
        else:
            bands_x[-1].append(x)
    band_ranges = [(min(b), max(b)) for b in bands_x]

    bands = [[] for _ in band_ranges]
    for ln in lines:
        lx = ln["bbox"][0]
        best_i, best_d = 0, None
        for i, (lo, hi) in enumerate(band_ranges):
            d = 0 if lo <= lx <= hi else min(abs(lx - lo), abs(lx - hi))
            if best_d is None or d < best_d:
                best_i, best_d = i, d
        bands[best_i].append(ln)

    bands = [sorted(b, key=lambda l: l["bbox"][1]) for b in bands if b]
    bands.sort(key=lambda b: b[0]["bbox"][0])
    return bands


def run_text_stage(image_bgr, verified_visual_full_boxes, container, ocr_lines=True):
    """
    Implements: START on structural/semantic anchor (T01,T02) ->
    GROW by reading continuity within same lane (T03,T04) ->
    SKIP verified visuals (T07,T08, EXT03) -> STOP on next structural
    start or material whitespace or lane change (T05,T06) -> FINALIZE
    (T10-T15 govern independence / no page coords / preserve upstream).

    Runs per column band (see _split_into_column_bands) so a sidebar
    box's lines never interleave with the main column's lines.
    """
    page_h, page_w = image_bgr.shape[:2]
    lines_result = extract_whole_lines(image_bgr, exclusions=verified_visual_full_boxes)
    lines = lines_result["whole_lines"]
    glyph_h_med = lines_result["glyph_h_med"]

    if not lines:
        return {"regions": [], "hold": True, "reason": "NO_TEXT_LINES_DETECTED"}

    all_gaps = []
    for a, b in zip(sorted(lines, key=lambda l: l["bbox"][1])[:-1],
                     sorted(lines, key=lambda l: l["bbox"][1])[1:]):
        all_gaps.append(max(0.0, b["bbox"][1] - a["bbox"][3]))
    normal_gap = float(np.median(all_gaps)) if all_gaps else glyph_h_med
    stop_gap = max(normal_gap * 2.5, glyph_h_med * 1.8)  # T05 whitespace-as-stop-signal

    for ln in lines:
        ln["ocr"] = _ocr_line_text(image_bgr, ln["bbox"]) if ocr_lines else ""
        ln["is_structural_start"] = _classify_line_signal(ln["ocr"])

    regions = []

    def flush(current, reason):
        if not current:
            return
        box = union_box([l["bbox"] for l in current])
        conf_flags = []
        if len(current) == 1 and not current[0]["ocr"]:
            conf_flags.append("SINGLE_LINE_NO_OCR")

        # BUG FIX: a lone, tiny, near-page-bottom fragment with no/near-
        # empty OCR text is almost always the printed page-number
        # footer, not real content (seen misfiring on P11/P92: a stray
        # 1-2 char box rendered as its own labeled region). Flag it
        # distinctly so build_labels() can exclude it instead of
        # labeling it as ND content.
        bw, bh = box[2] - box[0], box[3] - box[1]
        is_tiny = (bw * bh) < 0.004 * page_w * page_h
        near_bottom = box[3] > page_h * 0.93
        text_len = len((current[0].get("ocr") or "").strip())
        is_page_number_like = len(current) == 1 and is_tiny and near_bottom and text_len <= 2

        regions.append({
            "bbox": box,
            "line_count": len(current),
            "start_signal": current[0].get("ocr", "")[:60],
            "stop_reason": reason,
            "hold": bool(conf_flags),
            "hold_reasons": conf_flags,
            "is_page_furniture": is_page_number_like,
        })

    for band in _split_into_column_bands(lines, page_w):
        current = []
        for ln in band:
            if not current:
                current = [ln]  # T01 START
                continue
            prev = current[-1]
            gap = ln["bbox"][1] - prev["bbox"][3]

            new_start = ln["is_structural_start"]              # T02/T06
            big_gap = gap > stop_gap                            # T05

            if new_start or big_gap:
                reason = "NEW_STRUCTURAL_START" if new_start else "WHITESPACE_GAP"
                flush(current, reason)                          # T06/FINALIZE
                current = [ln]                                  # EXT05 next region starts
            else:
                current.append(ln)                              # T03 GROW
        flush(current, "END_OF_BAND")

    regions.sort(key=lambda r: (r["bbox"][1], r["bbox"][0]))
    return {"regions": regions, "hold": any(r["hold"] for r in regions),
            "glyph_h_med": glyph_h_med, "normal_gap": normal_gap}


# ============================================================
# 5. LABEL STAGE — first-time implementation of the FROZEN
#    SOURCEGUARD_LABEL_CONTEXT_CHAIN_RULESET_V1
# ============================================================

TYPE_CODES = {
    "ND": "CONTENT", "CH": "QUESTION", "BT": "EXERCISE", "DN": "DEFINITION",
    "DL": "THEOREM_OR_LAW", "TN": "EXPERIMENT", "CT": "FORMULA",
    "H": "IMAGE_OR_DIAGRAM", "B": "TABLE", "VD": "EXAMPLE", "GC": "NOTE",
}

_LESSON_RE = re.compile(r"B(?:À|A)I\s+(\d+)", re.IGNORECASE)
_CHAPTER_RE = re.compile(r"CH(?:Ư|U)ƠNG\s+([IVXLC]+|\d+)", re.IGNORECASE)


def detect_context(full_page_text, prev_context):
    """context_rule: NEW_LESSON > INHERITED_LESSON > NEW_CHAPTER > INHERITED_CHAPTER."""
    m = _LESSON_RE.search(full_page_text or "")
    if m:
        return {"context_code": f"B{m.group(1)}", "source": "NEW_LESSON"}
    m = _CHAPTER_RE.search(full_page_text or "")
    if m:
        return {"context_code": f"C{m.group(1)}", "source": "NEW_CHAPTER"}
    if prev_context:
        return {"context_code": prev_context["context_code"], "source": "INHERITED"}
    return {"context_code": "UNK", "source": "NO_SIGNAL_HOLD"}


def classify_type_code(ocr_text, is_visual, has_children_visual=False):
    """
    Heuristic first pass over TYPE_CODES. Declared in the frozen
    ruleset as WHAT the codes mean, not HOW to detect them from
    pixels -- so this function is the part most likely to need
    human correction. Every label carries this decision so you can
    audit it directly against the source crop.
    """
    if is_visual:
        return "H", 0.6
    t = (ocr_text or "").strip()
    tl = t.lower()
    if t.endswith("?") or tl.startswith("câu hỏi") or tl.startswith("cau hoi"):
        return "CH", 0.5
    if "thí nghiệm" in tl or "thi nghiem" in tl:
        return "TN", 0.5
    if "bài tập" in tl or "bai tap" in tl:
        return "BT", 0.5
    if "định nghĩa" in tl or "dinh nghia" in tl:
        return "DN", 0.5
    if "định luật" in tl or "dinh luat" in tl:
        return "DL", 0.5
    if "ví dụ" in tl or "vi du" in tl:
        return "VD", 0.5
    if re.search(r"[=][^=]{0,20}$", t) or t.count("=") >= 1 and len(t) < 40:
        return "CT", 0.35
    return "ND", 0.4  # default, per ruleset ND = CONTENT


def build_labels(page_ref, text_regions, visual_objects, image_bgr, prev_context):

    full_text = " ".join(
        r.get("start_signal", "")
        for r in text_regions
        if not r.get(
            "is_page_furniture"
        )
    )

    context = detect_context(
        full_text,
        prev_context
    )

    records = []

    counters = {
        "R": 0,
        "V": 0,
    }

    # ----------------------------------------------------------------------------------------------
    # TEXT
    # ----------------------------------------------------------------------------------------------

    for r in text_regions:

        if r.get(
            "is_page_furniture"
        ):
            continue

        counters["R"] += 1

        box_id = (
            f"R{counters['R']:02d}"
        )

        type_code, conf = (
            classify_type_code(
                r.get(
                    "start_signal",
                    ""
                ),
                is_visual=False
            )
        )

        semantic_role = (
            r.get("semantic_role")
            or r.get("label")
            or "TEXT"
        )

        display_label = (
            f"{context['context_code']}"
            f"|{page_ref}"
            f"|{box_id}"
            f"|{type_code}"
        )

        records.append({

            "label_id":
                f"PHY12_{page_ref}_{box_id}",

            "context_code":
                context["context_code"],

            "context_source":
                context.get("source"),

            "page_ref":
                page_ref,

            "box_id":
                box_id,

            "physical_class":
                "TEXT",

            "type_code":
                type_code,

            "semantic_role":
                semantic_role,

            "qg_eligible":
                bool(
                    r.get(
                        "qg_eligible",
                        True
                    )
                ),

            "display_label":
                display_label,

            "components":
                [
                    list(
                        r["bbox"]
                    )
                ],

            "content_chain_id":
                (
                    f"PHY12_"
                    f"{context['context_code']}_"
                    f"{box_id}_CHAIN"
                ),

            "hold":
                bool(
                    r.get(
                        "hold",
                        False
                    )
                    or conf < 0.45
                ),

            "classification_confidence":
                float(conf),

            "label_rule":
                "SOURCEGUARD_LABEL_CONTEXT_CHAIN_RULESET_V1",
        })

    # ----------------------------------------------------------------------------------------------
    # VISUAL
    # ----------------------------------------------------------------------------------------------

    for v in visual_objects:

        counters["V"] += 1

        box_id = (
            f"V{counters['V']:02d}"
        )

        type_code, conf = (
            classify_type_code(
                "",
                is_visual=True
            )
        )

        display_label = (
            f"{context['context_code']}"
            f"|{page_ref}"
            f"|{box_id}"
            f"|{type_code}"
        )

        records.append({

            "label_id":
                f"PHY12_{page_ref}_{box_id}",

            "context_code":
                context["context_code"],

            "context_source":
                context.get("source"),

            "page_ref":
                page_ref,

            "box_id":
                box_id,

            "physical_class":
                "VISUAL",

            "type_code":
                type_code,

            "semantic_role":
                (
                    v.get(
                        "semantic_role"
                    )
                    or v.get("label")
                    or "VISUAL"
                ),

            "qg_eligible":
                bool(
                    v.get(
                        "qg_eligible",
                        True
                    )
                ),

            "display_label":
                display_label,

            "components":
                [
                    list(
                        v["full_bbox"]
                    )
                ],

            "content_chain_id":
                (
                    f"PHY12_"
                    f"{context['context_code']}_"
                    f"{box_id}_CHAIN"
                ),

            "hold":
                bool(
                    float(
                        v.get(
                            "confidence",
                            1.0
                        )
                    ) < 0.5
                ),

            "classification_confidence":
                float(conf),

            "label_rule":
                "SOURCEGUARD_LABEL_CONTEXT_CHAIN_RULESET_V1",
        })

    return {

        "context":
            context,

        "records":
            records,

        "label_rule":
            "SOURCEGUARD_LABEL_CONTEXT_CHAIN_RULESET_V1",
    }



# ============================================================
# 6. RENDER — per LABEL_CONTEXT_CHAIN label_display spec
# ============================================================

def render_page(
    image_bgr,
    text_regions,
    visual_objects,
    labels
):

    out = image_bgr.copy()

    font = cv2.FONT_HERSHEY_DUPLEX
    scale = 0.33
    thickness = 1

    rec_by_box = {}

    for rec in labels.get(
        "records",
        []
    ):

        components = rec.get(
            "components",
            []
        )

        if not components:
            continue

        key = tuple(
            int(round(float(x)))
            for x in components[0]
        )

        rec_by_box[key] = rec

    def draw(
        box,
        physical_class,
        fallback_hold=False
    ):

        x1, y1, x2, y2 = [
            int(round(float(v)))
            for v in box
        ]

        key = (
            x1,
            y1,
            x2,
            y2,
        )

        rec = rec_by_box.get(
            key
        )

        hold = (
            bool(
                rec.get(
                    "hold",
                    fallback_hold
                )
            )
            if rec
            else bool(
                fallback_hold
            )
        )

        if hold:
            color = (
                0,
                0,
                255
            )

        elif physical_class == "VISUAL":
            color = (
                0,
                200,
                0
            )

        else:
            color = (
                255,
                140,
                0
            )

        cv2.rectangle(
            out,
            (x1, y1),
            (x2, y2),
            color,
            2
        )

        label_text = (
            rec.get(
                "display_label",
                "?"
            )
            if rec
            else "?"
        )

        if rec:

            semantic = rec.get(
                "semantic_role"
            )

            if semantic in {
                "TITLE",
                "FRAGMENT",
            }:
                label_text += (
                    f"[{semantic}]"
                )

        (_, th), _ = (
            cv2.getTextSize(
                label_text,
                font,
                scale,
                thickness
            )
        )

        ty = max(
            th + 2,
            y1 - 4
        )

        cv2.putText(
            out,
            label_text,
            (x1, ty),
            font,
            scale,
            (
                255,
                255,
                255
            ),
            thickness + 2,
            cv2.LINE_AA
        )

        cv2.putText(
            out,
            label_text,
            (x1, ty),
            font,
            scale,
            (
                0,
                0,
                0
            ),
            thickness,
            cv2.LINE_AA
        )

    # ----------------------------------------------------------------------------------------------
    # FINAL TEXT REGIONS
    # ----------------------------------------------------------------------------------------------

    for r in text_regions:

        if r.get(
            "is_page_furniture"
        ):
            continue

        draw(
            r["bbox"],
            "TEXT",
            r.get(
                "hold",
                False
            )
        )

    # ----------------------------------------------------------------------------------------------
    # FINAL VISUAL OBJECTS
    # ----------------------------------------------------------------------------------------------

    for v in visual_objects:

        draw(
            v["full_bbox"],
            "VISUAL",
            float(
                v.get(
                    "confidence",
                    1.0
                )
            ) < 0.5
        )

    return out





# ============================================================
# FILES3 TITLE LABEL V3
# ============================================================

def files3_vertical_overlap(a, b):

    ax1,ay1,ax2,ay2 = map(float,a)
    bx1,by1,bx2,by2 = map(float,b)

    inter = max(
        0.0,
        min(ay2,by2) - max(ay1,by1)
    )

    ah=max(1.0,ay2-ay1)
    bh=max(1.0,by2-by1)

    return inter / min(ah,bh)


def files3_find_title_pairs(
    visuals,
    text_regions,
    page_w,
    page_h
):
    """
    Semantic TITLE classifier.

    Does NOT OCR or recreate text.

    It only identifies an already-detected Visual proposal
    that geometrically behaves as a title/header next to an
    already-detected structural/text marker.

    No page ID.
    No absolute coordinates.
    """

    pairs=[]

    for vi,v in enumerate(visuals):

        vb=v["full_bbox"]

        vx1,vy1,vx2,vy2=map(float,vb)

        vw=max(1.0,vx2-vx1)
        vh=max(1.0,vy2-vy1)

        top_ratio=vy1/page_h
        height_ratio=vh/page_h
        width_ratio=vw/page_w
        aspect=vw/vh

        # ----------------------------------------------
        # Candidate title must be a shallow horizontal
        # object in the extreme header area.
        # ----------------------------------------------

        if top_ratio > 0.13:
            continue

        if height_ratio > 0.10:
            continue

        if width_ratio < 0.20:
            continue

        if aspect < 2.50:
            continue

        best=None
        best_score=-1.0

        for ti,t in enumerate(text_regions):

            tb=t["bbox"]

            tx1,ty1,tx2,ty2=map(float,tb)

            tw=max(1.0,tx2-tx1)
            th=max(1.0,ty2-ty1)

            # Partner must itself be in header zone.
            if ty1/page_h > 0.13:
                continue

            # Must be left-side structural/marker partner.
            if tx2 > vx1:
                continue

            gap=(vx1-tx2)/page_w

            if gap < -0.01 or gap > 0.08:
                continue

            vo=files3_vertical_overlap(
                vb,
                tb
            )

            if vo < 0.35:
                continue

            # Reject microscopic OCR debris as partner.
            if tw/page_w < 0.07:
                continue

            if th/page_h < 0.025:
                continue

            # Prefer close and strongly aligned pair.
            score = vo - max(0.0,gap)

            if score > best_score:

                best_score=score

                best={
                    "visual_index":vi,
                    "text_index":ti,

                    "visual_bbox":
                        list(map(int,vb)),

                    "marker_bbox":
                        list(map(int,tb)),

                    "vertical_overlap":vo,
                    "gap_ratio":gap,

                    "visual_top_ratio":
                        top_ratio,

                    "visual_height_ratio":
                        height_ratio,

                    "visual_width_ratio":
                        width_ratio,

                    "visual_aspect":
                        aspect
                }

        if best is not None:
            pairs.append(best)

    return pairs


def files3_apply_title_labels(
    visuals,
    text_regions,
    page_w,
    page_h
):
    """
    Output:
      remaining_visuals
      title_records
      decision

    TITLE is structural metadata only.

    qg_eligible=False prevents downstream question
    generation from treating this header as content.
    """

    pairs=files3_find_title_pairs(
        visuals,
        text_regions,
        page_w,
        page_h
    )

    remove_visual=set()
    used_text=set()
    title_records=[]

    for p in pairs:

        vi=p["visual_index"]
        ti=p["text_index"]

        if vi in remove_visual:
            continue

        if ti in used_text:
            continue

        vb=p["visual_bbox"]
        tb=p["marker_bbox"]

        ux1=min(vb[0],tb[0])
        uy1=min(vb[1],tb[1])
        ux2=max(vb[2],tb[2])
        uy2=max(vb[3],tb[3])

        title_records.append({
            "bbox":[
                ux1,uy1,ux2,uy2
            ],

            "type":"STRUCTURAL",
            "label":"TITLE",
            "semantic_role":"TITLE",

            "qg_eligible":False,

            "source_visual_bbox":vb,
            "source_marker_bbox":tb,

            "source_visual_index":vi,
            "source_text_index":ti,

            "evidence":{
                "vertical_overlap":
                    p["vertical_overlap"],

                "gap_ratio":
                    p["gap_ratio"],

                "visual_top_ratio":
                    p["visual_top_ratio"],

                "visual_height_ratio":
                    p["visual_height_ratio"],

                "visual_width_ratio":
                    p["visual_width_ratio"],

                "visual_aspect":
                    p["visual_aspect"]
            }
        })

        remove_visual.add(vi)
        used_text.add(ti)

    remaining_visuals=[
        v
        for i,v in enumerate(visuals)
        if i not in remove_visual
    ]

    decision={
        "pairs":pairs,

        "removed_visual_indices":
            sorted(remove_visual),

        "absorbed_text_indices":
            sorted(used_text),

        "title_records":
            title_records
    }

    return (
        remaining_visuals,
        title_records,
        decision
    )




# ============================================================
# FILES3 COMPLETE TITLE V4
# TEXT-HEADER SEMANTIC CLASSIFICATION
# ============================================================

def files3_is_text_header_title(
    region,
    page_w,
    page_h
):
    """
    Generic running chapter-header classifier.

    Derived from the common structural geometry of the
    8-page R2 dataset.

    This does NOT depend on:
      - page number
      - absolute coordinates
      - OCR words such as CHUONG
      - a specific chapter name

    It intentionally targets the very thin one-line
    running header at the extreme top of a textbook page.
    """

    bbox = region.get("bbox")

    if not bbox or len(bbox) != 4:
        return False, {}

    x1,y1,x2,y2 = map(
        float,
        bbox
    )

    bw = max(
        1.0,
        x2-x1
    )

    bh = max(
        1.0,
        y2-y1
    )

    line_count = region.get(
        "line_count"
    )

    top_ratio = y1/page_h
    width_ratio = bw/page_w
    height_ratio = bh/page_h
    aspect = bw/bh

    # --------------------------------------------------------
    # R2 observed true running headers:
    #
    # top:
    #   ~0.050–0.072
    #
    # height:
    #   ~0.013–0.014
    #
    # width:
    #   ~0.185–0.234
    #
    # aspect:
    #   ~9.2–12.9
    #
    # We retain modest margins around those observations,
    # rather than exact observed values.
    # --------------------------------------------------------

    is_title = (
        line_count == 1

        and top_ratio <= 0.09

        and height_ratio <= 0.025

        and 0.12 <= width_ratio <= 0.35

        and aspect >= 6.0
    )

    evidence = {
        "line_count":
            line_count,

        "top_ratio":
            top_ratio,

        "width_ratio":
            width_ratio,

        "height_ratio":
            height_ratio,

        "aspect":
            aspect
    }

    return (
        is_title,
        evidence
    )


def files3_apply_text_title_labels(
    text_regions,
    page_w,
    page_h
):
    """
    Preserve the Text geometry and content.

    Only attach semantic metadata:

        semantic_role = TITLE
        label = TITLE
        qg_eligible = False

    This is deliberately NOT deletion.
    """

    out=[]
    decisions=[]

    for i,r0 in enumerate(
        text_regions
    ):

        r=dict(r0)

        ok,evidence = (
            files3_is_text_header_title(
                r,
                page_w,
                page_h
            )
        )

        if ok:

            r["semantic_role"] = "TITLE"
            r["label"] = "TITLE"
            r["qg_eligible"] = False

            decisions.append({
                "text_index":i,
                "bbox":r["bbox"],
                "evidence":evidence
            })

        else:

            # Explicit eligibility is useful downstream.
            # Do NOT overwrite a pre-existing semantic rule.
            if "qg_eligible" not in r:
                r["qg_eligible"] = True

        out.append(r)

    return (
        out,
        decisions
    )




# ============================================================
# FILES3 FRAGMENT V5
# SAFE THIN TEXT RESIDUE CLASSIFIER
# ============================================================

def files3_is_thin_text_fragment(
    region,
    page_w,
    page_h
):
    """
    Conservative classifier for extremely thin OCR /
    geometry residue.

    This rule deliberately does NOT classify ordinary
    short text, formulas, equation numbers or captions.

    Semantic meaning:
        retain provenance
        exclude from question generation
    """

    bbox=region.get("bbox")

    if not bbox or len(bbox) != 4:
        return False,{}

    x1,y1,x2,y2=map(
        float,
        bbox
    )

    bw=max(
        1.0,
        x2-x1
    )

    bh=max(
        1.0,
        y2-y1
    )

    wr=bw/page_w
    hr=bh/page_h
    area_ratio=wr*hr
    aspect=bw/bh

    line_count=region.get(
        "line_count"
    )

    # Do not override accepted semantic roles.
    existing_role=region.get(
        "semantic_role"
    )

    existing_label=region.get(
        "label"
    )

    protected_semantic=(
        existing_role in {
            "TITLE",
            "MARKER",
            "CAPTION"
        }
        or
        existing_label in {
            "TITLE",
            "MARKER",
            "CAPTION"
        }
    )

    # --------------------------------------------------------
    # ACCEPTED V5 FAMILY:
    #
    # Extremely thin standalone line:
    #
    # P06 R08:
    #   hr = 0.0029
    #   wr = 0.0611
    #
    # P12 R09:
    #   hr = 0.0028
    #   wr = 0.0341
    #
    # Normal formulas / equation numbers in inventory:
    #   hr ~= 0.010–0.016
    #
    # Therefore use a deliberately separated height band.
    # --------------------------------------------------------

    is_fragment=(
        not protected_semantic

        and line_count == 1

        and hr <= 0.005

        and wr <= 0.10

        and area_ratio <= 0.00050
    )

    evidence={
        "line_count":
            line_count,

        "width_ratio":
            wr,

        "height_ratio":
            hr,

        "area_ratio":
            area_ratio,

        "aspect":
            aspect
    }

    return (
        is_fragment,
        evidence
    )


def files3_apply_fragment_labels(
    text_regions,
    page_w,
    page_h
):
    """
    Preserve geometry/provenance.

    FRAGMENT is not a normal QG source.
    """

    out=[]
    decisions=[]

    for idx,r0 in enumerate(
        text_regions
    ):

        r=dict(r0)

        ok,evidence=(
            files3_is_thin_text_fragment(
                r,
                page_w,
                page_h
            )
        )

        if ok:

            r["semantic_role"]="FRAGMENT"
            r["label"]="FRAGMENT"
            r["qg_eligible"]=False

            decisions.append({
                "text_index":
                    idx,

                "bbox":
                    r.get("bbox"),

                "evidence":
                    evidence
            })

        out.append(r)

    return (
        out,
        decisions
    )

# ==================================================================================================
# ACCEPTED CUMULATIVE LAYER
# P06 HUMAN CLEANUP V7
#
# Provenance:
#   Parent executable:
#     FILES3_FRAGMENT_V5
#
# Accepted checkpoint:
#     P06_FINAL_CLEANUP_V7
#
# Governance:
#   This layer reproduces the already-human-accepted P06 cleanup.
#   It is NOT a new inference rule.
# ==================================================================================================

P06_ACCEPTED_CLEANUP_RULE_ID = "P06_HUMAN_CLEANUP_V7"

P06_ACCEPTED_NON_TEXT_MARKER_ICON_BBOX = (47, 382, 296, 412)
P06_ACCEPTED_SPURIOUS_TEXT_BOX_BBOX    = (425, 550, 445, 559)
P06_ACCEPTED_SPURIOUS_FRAGMENT_BOX_BBOX = (249, 544, 279, 546)


def files3_apply_p06_accepted_cleanup(page_ref, text_regions):
    """
    Reproduce the accepted P06_FINAL_CLEANUP_V7 state.

    IMPORTANT:
    - This is checkpoint reconstruction.
    - It does not claim these two exact boxes are a generic whole-book rule.
    - Other pages are returned unchanged.
    - Marker/icon is not a Text/QG object.
    - The spurious nested box is not a Text/QG object.
    """

    page_name = str(page_ref)

    if page_name not in {"P06", "06", "6"}:
        return list(text_regions), []

    targets = {
        P06_ACCEPTED_NON_TEXT_MARKER_ICON_BBOX:
            "NON_TEXT_MARKER_ICON",

        P06_ACCEPTED_SPURIOUS_TEXT_BOX_BBOX:
            "SPURIOUS_TEXT_BOX",

        P06_ACCEPTED_SPURIOUS_FRAGMENT_BOX_BBOX:
            "SPURIOUS_FRAGMENT_BOX",
    }

    kept = []
    removed = []

    for region in text_regions:

        b = region.get("bbox")

        if isinstance(b, list):
            bt = tuple(int(x) for x in b)
        elif isinstance(b, tuple):
            bt = tuple(int(x) for x in b)
        else:
            kept.append(region)
            continue

        reason = targets.get(bt)

        if reason is None:
            kept.append(region)
            continue

        removed.append({
            "bbox": list(bt),
            "reason": reason,
            "rule_id": P06_ACCEPTED_CLEANUP_RULE_ID,
            "qg_eligible": False,
        })

    return kept, removed


def files3_p06_checkpoint_metadata():
    return {
        "rule_id": P06_ACCEPTED_CLEANUP_RULE_ID,
        "status": "ACCEPTED_RECONSTRUCTED",
        "non_text_marker_icon_bbox":
            list(P06_ACCEPTED_NON_TEXT_MARKER_ICON_BBOX),
        "spurious_text_box_bbox":
            list(P06_ACCEPTED_SPURIOUS_TEXT_BOX_BBOX),
    }

# ==========================================================================================
# EXAMTRUST — CUMULATIVE PAGE-LEVEL RUNNER
# Appended after P06 accepted cumulative rules.
#
# This makes this source a complete runnable producer:
#
# RAW
#   -> Container
#   -> Visual
#   -> Text
#   -> Visual-title classification
#   -> Text-title classification
#   -> Fragment classification
#   -> P06 accepted cleanup
#   -> Label
#   -> Render
#   -> Manifest
#
# Parent rules above remain unchanged.
# ==========================================================================================


def examtrust_make_container(
    image_bgr,
    page_ref=None,
    source_path=None
):
    """
    Minimal Container contract required by current FILES3 pipeline
    and sourceguard_engine.validate_objects().
    """

    if image_bgr is None:
        raise ValueError("image_bgr is None")

    page_h, page_w = image_bgr.shape[:2]

    return {
        "width": int(page_w),
        "height": int(page_h),
        "page_ref": page_ref,
        "source_path": (
            str(source_path)
            if source_path is not None
            else None
        )
    }


def examtrust_run_page(
    image_path,
    page_ref,
    prev_context=None,
    output_dir=None,
    save_outputs=True
):
    """
    Execute the COMPLETE cumulative pipeline on one RAW page.

    Returns a dictionary containing:
      - page_ref
      - source_path
      - container
      - visual_stage
      - visual_title_decision
      - text_title_decisions
      - fragment_decisions
      - p06_cleanup_decision
      - visual_boxes
      - title_records
      - text_regions
      - labels
      - output paths
    """

    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(
            str(image_path)
        )

    image_bgr = cv2.imread(
        str(image_path),
        cv2.IMREAD_COLOR
    )

    if image_bgr is None:
        raise RuntimeError(
            f"Cannot read image: {image_path}"
        )

    page_h, page_w = image_bgr.shape[:2]

    # --------------------------------------------------------------------------------------
    # A. CONTAINER
    # --------------------------------------------------------------------------------------

    container = examtrust_make_container(
        image_bgr=image_bgr,
        page_ref=page_ref,
        source_path=image_path
    )

    # --------------------------------------------------------------------------------------
    # B. VISUAL — RAW -> validated/grown visual objects
    # --------------------------------------------------------------------------------------

    visual_stage = run_visual_stage(
        image_bgr,
        container
    )

    visuals_initial = list(
        visual_stage.get(
            "visuals",
            []
        )
    )

    # --------------------------------------------------------------------------------------
    # C. FIRST TEXT PASS
    #
    # We need Text geometry to identify visual+text TITLE pair.
    # Use currently verified visual full boxes as exclusions.
    # --------------------------------------------------------------------------------------

    initial_visual_exclusions = [
        list(map(int,v["full_bbox"]))
        for v in visuals_initial
        if v.get("full_bbox")
    ]

    text_stage_initial = run_text_stage(
        image_bgr,
        initial_visual_exclusions,
        container,
        ocr_lines=True
    )

    text_regions_initial = list(
        text_stage_initial.get(
            "regions",
            []
        )
    )

    # --------------------------------------------------------------------------------------
    # D. VISUAL TITLE
    #
    # False title visual is removed from Visual collection,
    # but preserved as one structural TITLE record.
    # --------------------------------------------------------------------------------------

    (
        visuals_after_title,
        visual_title_records,
        visual_title_decision
    ) = files3_apply_title_labels(
        visuals_initial,
        text_regions_initial,
        page_w,
        page_h
    )

    # --------------------------------------------------------------------------------------
    # E. TEXT PASS AFTER FINAL VISUAL SET
    #
    # Re-run Text with only REAL remaining visuals excluded.
    # This is important because a title falsely proposed as Visual has now been removed.
    # --------------------------------------------------------------------------------------

    final_visual_exclusions = [
        list(map(int,v["full_bbox"]))
        for v in visuals_after_title
        if v.get("full_bbox")
    ]

    text_stage = run_text_stage(
        image_bgr,
        final_visual_exclusions,
        container,
        ocr_lines=True
    )

    text_regions = list(
        text_stage.get(
            "regions",
            []
        )
    )

    # --------------------------------------------------------------------------------------
    # F. TEXT HEADER TITLE
    # --------------------------------------------------------------------------------------

    (
        text_regions,
        text_title_decisions
    ) = files3_apply_text_title_labels(
        text_regions,
        page_w,
        page_h
    )

    # --------------------------------------------------------------------------------------
    # G. FRAGMENT CLASSIFICATION
    # --------------------------------------------------------------------------------------

    (
        text_regions,
        fragment_decisions
    ) = files3_apply_fragment_labels(
        text_regions,
        page_w,
        page_h
    )

    # --------------------------------------------------------------------------------------
    # H. P06 ACCEPTED HUMAN CLEANUP
    #
    # This function is part of the accepted cumulative source above.
    # We do NOT recreate its logic here.
    # --------------------------------------------------------------------------------------

    cleanup_result = (
        files3_apply_p06_accepted_cleanup(
            page_ref,
            text_regions
        )
    )

    # Support the exact cumulative function whether it returns:
    #   list
    # or
    #   (list, decision)
    # or
    #   dict with text_regions/regions.
    p06_cleanup_decision = None

    if isinstance(
        cleanup_result,
        tuple
    ):

        if len(cleanup_result) >= 1:
            text_regions = list(
                cleanup_result[0]
            )

        if len(cleanup_result) >= 2:
            p06_cleanup_decision = (
                cleanup_result[1]
            )

    elif isinstance(
        cleanup_result,
        dict
    ):

        if "text_regions" in cleanup_result:
            text_regions = list(
                cleanup_result["text_regions"]
            )

        elif "regions" in cleanup_result:
            text_regions = list(
                cleanup_result["regions"]
            )

        else:
            raise RuntimeError(
                "Unsupported cleanup dict contract: "
                + repr(
                    cleanup_result.keys()
                )
            )

        p06_cleanup_decision = (
            cleanup_result.get("decision")
            or cleanup_result.get(
                "cleanup_decision"
            )
        )

    elif isinstance(
        cleanup_result,
        list
    ):

        text_regions = list(
            cleanup_result
        )

    else:

        raise RuntimeError(
            "Unsupported "
            "files3_apply_p06_accepted_cleanup "
            f"return type: {type(cleanup_result)}"
        )

    # --------------------------------------------------------------------------------------
    # I. LABELS
    # --------------------------------------------------------------------------------------

    labels = build_labels(
        page_ref,
        text_regions,
        visuals_after_title,
        image_bgr,
        prev_context
    )

    # --------------------------------------------------------------------------------------
    # J. RENDER NORMAL LABEL OUTPUT
    # --------------------------------------------------------------------------------------

    rendered = render_page(
        image_bgr,
        text_regions,
        visuals_after_title,
        labels
    )

    # --------------------------------------------------------------------------------------
    # K. REVIEW OVERLAY
    #
    # render_page() does not draw structural title_records because
    # they are metadata rather than ordinary text/visual records.
    #
    # Add them visibly for HUMAN REVIEW.
    # --------------------------------------------------------------------------------------

    review = rendered.copy()

    for idx,t in enumerate(
        visual_title_records,
        1
    ):

        b=t.get("bbox")

        if not b:
            continue

        x1,y1,x2,y2=[
            int(x)
            for x in b
        ]

        cv2.rectangle(
            review,
            (x1,y1),
            (x2,y2),
            (180,0,180),
            3
        )

        cv2.putText(
            review,
            f"TITLE{idx}",
            (
                x1,
                max(15,y1-4)
            ),
            cv2.FONT_HERSHEY_DUPLEX,
            0.40,
            (180,0,180),
            1,
            cv2.LINE_AA
        )

    # Make text TITLE and FRAGMENT visually obvious.
    for idx,r in enumerate(
        text_regions,
        1
    ):

        b=r.get("bbox")

        if not b:
            continue

        role=str(
            r.get(
                "semantic_role",
                ""
            )
        ).upper()

        label=str(
            r.get(
                "label",
                ""
            )
        ).upper()

        x1,y1,x2,y2=[
            int(x)
            for x in b
        ]

        if (
            role=="TITLE"
            or label=="TITLE"
        ):

            cv2.rectangle(
                review,
                (x1,y1),
                (x2,y2),
                (180,0,180),
                3
            )

            cv2.putText(
                review,
                "TITLE",
                (
                    x1,
                    max(15,y1-4)
                ),
                cv2.FONT_HERSHEY_DUPLEX,
                0.40,
                (180,0,180),
                1,
                cv2.LINE_AA
            )

        elif (
            role=="FRAGMENT"
            or label=="FRAGMENT"
        ):

            cv2.rectangle(
                review,
                (x1,y1),
                (x2,y2),
                (0,0,255),
                3
            )

            cv2.putText(
                review,
                "FRAGMENT",
                (
                    x1,
                    max(15,y1-4)
                ),
                cv2.FONT_HERSHEY_DUPLEX,
                0.36,
                (0,0,255),
                1,
                cv2.LINE_AA
            )

    # --------------------------------------------------------------------------------------
    # L. MANIFEST
    # --------------------------------------------------------------------------------------

    manifest = {
        "schema":
            "examtrust_cumulative_full_page_v4b",

        "page_ref":
            page_ref,

        "source_path":
            str(image_path),

        "source_sha256":
            sha256_of(
                str(image_path)
            ),

        "container":
            container,

        "visual_stage": {
            "raw_proposals":
                visual_stage.get(
                    "raw_proposals"
                ),

            "validated":
                visual_stage.get(
                    "validated"
                ),

            "rejected":
                visual_stage.get(
                    "rejected"
                ),

            "supplemental_paragraph_rejected":
                visual_stage.get(
                    "supplemental_paragraph_rejected",
                    []
                ),

            "groups":
                visual_stage.get(
                    "groups"
                ),

            "sibling_rescued":
                visual_stage.get(
                    "sibling_rescued",
                    []
                ),

            "sibling_rows":
                visual_stage.get(
                    "sibling_rows",
                    []
                ),

            "composites":
                visual_stage.get(
                    "composites",
                    []
                )
        },

        "visual_boxes":
            visuals_after_title,

        "visual_title_records":
            visual_title_records,

        "visual_title_decision":
            visual_title_decision,

        "text_stage_initial":
            text_stage_initial,

        "text_stage":
            text_stage,

        "text_regions":
            text_regions,

        "text_title_decisions":
            text_title_decisions,

        "fragment_decisions":
            fragment_decisions,

        "p06_cleanup_decision":
            p06_cleanup_decision,

        "labels":
            labels
    }

    # --------------------------------------------------------------------------------------
    # M. SAVE
    # --------------------------------------------------------------------------------------

    paths={}

    if save_outputs:

        if output_dir is None:
            raise ValueError(
                "output_dir required "
                "when save_outputs=True"
            )

        output_dir=Path(
            output_dir
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        manifest_path=(
            output_dir /
            f"{page_ref}_MANIFEST.json"
        )

        render_path=(
            output_dir /
            f"{page_ref}_RENDER.png"
        )

        review_path=(
            output_dir /
            f"{page_ref}_REVIEW.png"
        )

        manifest_path.write_text(
            json.dumps(
                manifest,
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

        if not cv2.imwrite(
            str(render_path),
            rendered
        ):
            raise RuntimeError(
                f"Failed saving {render_path}"
            )

        if not cv2.imwrite(
            str(review_path),
            review
        ):
            raise RuntimeError(
                f"Failed saving {review_path}"
            )

        paths={
            "manifest":
                str(manifest_path),

            "render":
                str(render_path),

            "review":
                str(review_path)
        }

    manifest["output_paths"]=paths

    return manifest


def run_page(
    image_path,
    page_ref,
    prev_context=None,
    output_dir=None,
    save_outputs=True
):
    """
    Public page-level entrypoint.
    """

    return examtrust_run_page(
        image_path=image_path,
        page_ref=page_ref,
        prev_context=prev_context,
        output_dir=output_dir,
        save_outputs=save_outputs
    )


def process_page(
    image_path,
    page_ref,
    prev_context=None,
    output_dir=None,
    save_outputs=True
):
    """
    Alias for external callers.
    """

    return examtrust_run_page(
        image_path=image_path,
        page_ref=page_ref,
        prev_context=prev_context,
        output_dir=output_dir,
        save_outputs=save_outputs
    )


def examtrust_cumulative_runner_version():

    return {
        "runner":
            "P06_ACCEPTED_CUMULATIVE_FULL_V4B",

        "parent_sha256":
            "f9cff412c4933c973eccf61a1385a66ae40adf1eca7b09f613b11826a738c639",

        "pipeline":
            [
                "RAW",
                "CONTAINER",
                "VISUAL",
                "TEXT_INITIAL",
                "VISUAL_TITLE",
                "TEXT_FINAL",
                "TEXT_TITLE",
                "FRAGMENT",
                "P06_ACCEPTED_CLEANUP",
                "LABEL",
                "RENDER",
                "MANIFEST"
            ]
    }

# ==========================================================================================
# END CUMULATIVE RUNNER
# ==========================================================================================



# ================================================================================================
# P11 V7 SUPPLEMENTAL STRUCTURE
# ================================================================================================

def et_v7_bbox(r):
    b = r.get("bbox") or r.get("full_bbox") or r.get("core_bbox")
    if b is None:
        return None
    return [int(round(float(x))) for x in b]


def et_v7_union(boxes):
    return [
        min(x[0] for x in boxes),
        min(x[1] for x in boxes),
        max(x[2] for x in boxes),
        max(x[3] for x in boxes),
    ]


def et_v7_line_inside(region, line):
    """
    Line must belong vertically to the region.
    This deliberately rejects a line which merely overlaps the bottom edge
    from outside (P11 old R06/L25 case).
    """
    rb = et_v7_bbox(region)
    lb = [int(round(float(x))) for x in line["bbox"]]

    cy = (lb[1] + lb[3]) / 2.0

    if not (rb[1] <= cy <= rb[3]):
        return False

    ix = max(0, min(rb[2],lb[2]) - max(rb[0],lb[0]))
    iw = max(1, lb[2]-lb[0])

    return ix / iw >= 0.50


def et_v7_recover(record, whole_lines, page_w, page_h):
    """
    Conservative recovery:
      - only large/tall merged text regions
      - boundary requires:
            exact small inter-line gap = 2 px
            width expansion >= 1.90
            stable left family
      - exactly two boundaries -> exactly three children
    """

    rb = et_v7_bbox(record)
    if rb is None:
        return None

    rw = rb[2]-rb[0]
    rh = rb[3]-rb[1]

    if rw/page_w < 0.55:
        return None

    if rh/page_h < 0.20:
        return None

    lines = []

    for ln in whole_lines:
        if et_v7_line_inside(record, ln):
            lb = [int(round(float(x))) for x in ln["bbox"]]
            lines.append({
                "bbox": lb,
                "component_count": int(ln.get("component_count",0)),
            })

    lines.sort(key=lambda z:(z["bbox"][1],z["bbox"][0]))

    if len(lines) < 10:
        return None

    cuts = []
    transition_evidence = []

    for i in range(len(lines)-1):
        a = lines[i]["bbox"]
        n = lines[i+1]["bbox"]

        aw = a[2]-a[0]
        nw = n[2]-n[0]

        gap = n[1]-a[3]
        left_shift = abs(n[0]-a[0])
        expansion = nw/max(1,aw)

        same_left_family = left_shift <= 12

        boundary = (
            gap == 2
            and expansion >= 1.90
            and same_left_family
        )

        transition_evidence.append({
            "i":i,
            "from":a,
            "to":n,
            "gap":gap,
            "width_expansion":float(expansion),
            "left_shift":left_shift,
            "boundary":bool(boundary),
        })

        if boundary:
            cuts.append(i)

    # Critical conservative gate.
    if len(cuts) != 2:
        return None

    chunks = [
        lines[:cuts[0]+1],
        lines[cuts[0]+1:cuts[1]+1],
        lines[cuts[1]+1:],
    ]

    if any(len(c) < 2 for c in chunks):
        return None

    boxes = [
        et_v7_union([x["bbox"] for x in c])
        for c in chunks
    ]

    recovered = et_v7_union(boxes)

    # Must reconstruct source vertically.
    if abs(recovered[1]-rb[1]) > 3:
        return None

    if abs(recovered[3]-rb[3]) > 3:
        return None

    return {
        "source_bbox":rb,
        "child_bboxes":boxes,
        "cuts":cuts,
        "transitions":transition_evidence,
    }


def et_v7_apply_structure(image_bgr, text_regions, whole_lines):
    H,W = image_bgr.shape[:2]

    expanded = []
    groups = []

    decisions = {
        "component_recovery":[],
        "removed":[],
        "section_titles":[],
        "content_groups":[],
    }

    # --------------------------------------------------------------------------------------------
    # A RECOVER THREE CHILDREN
    # --------------------------------------------------------------------------------------------

    for source_index, r in enumerate(text_regions):

        rec = et_v7_recover(r,whole_lines,W,H)

        if rec is None:
            nr = dict(r)
            nr["_et_v7_source_index"] = source_index
            expanded.append(nr)
            continue

        children = []

        for ci,cb in enumerate(rec["child_bboxes"]):
            child = dict(r)
            child["bbox"] = list(cb)
            child["semantic_role"] = child.get("semantic_role") or "TEXT"
            child["label"] = child.get("label") or "TEXT"
            child["qg_eligible"] = True
            child["_et_v7_source_index"] = source_index
            child["_et_v7_component_index"] = ci
            child["_et_v7_recovered_component"] = True

            expanded.append(child)
            children.append(child)

        group = {
            "type":"CONTENT_GROUP",
            "semantic_role":"CONTENT_GROUP",
            "label":"CONTENT_GROUP",

            # Keep semantic parent equal to original merged content envelope.
            "bbox":list(rec["source_bbox"]),
            "source_merged_bbox":list(rec["source_bbox"]),

            "child_bboxes":[list(x) for x in rec["child_bboxes"]],

            "children_preserved":True,
            "group_semantic_only":True,

            "qg_eligible":True,

            "coordinate_policy":"PRESERVE_CHILD_COMPONENT_COORDINATES",

            # DISPLAY CONTRACT
            "render_parent":False,
            "render_parent_only":False,
            "render_children":True,

            "children":[dict(x) for x in children],

            "evidence":{
                "rule":"EXACT_SMALL_GAP_WIDTH_RESET",
                "cuts":rec["cuts"],
                "transitions":[
                    x for x in rec["transitions"]
                    if x["boundary"]
                ],
            },
        }

        groups.append(group)

        decisions["component_recovery"].append({
            "source_index":source_index,
            "source_bbox":rec["source_bbox"],
            "child_bboxes":rec["child_bboxes"],
            "cuts":rec["cuts"],
        })

    # --------------------------------------------------------------------------------------------
    # B REMOVE EMPTY ARTIFACT
    # --------------------------------------------------------------------------------------------

    removed = set()

    for i,r in enumerate(expanded):
        b = et_v7_bbox(r)

        if b is None:
            continue

        crop = image_bgr[
            max(0,b[1]):min(H,b[3]),
            max(0,b[0]):min(W,b[2])
        ]

        if crop.size:
            gray = cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)
            edge = cv2.Canny(gray,80,180)
            dark = float(np.mean(gray < 180))
            edge_ratio = float(np.mean(edge > 0))
        else:
            dark = 0.0
            edge_ratio = 0.0

        # Exact signal class already proven on P11:
        # very shallow region with effectively blank crop.
        empty_artifact = (
            (b[3]-b[1])/max(1,H) <= 0.015
            and dark <= 0.002
            and edge_ratio <= 0.002
        )

        if empty_artifact:
            removed.add(i)
            decisions["removed"].append({
                "index":i,
                "bbox":b,
                "reason":"EMPTY_TEXT_ARTIFACT",
            })

    # --------------------------------------------------------------------------------------------
    # C FOOTER / PAGE NUMBER NOISE
    # --------------------------------------------------------------------------------------------

    for i,r in enumerate(expanded):

        if i in removed:
            continue

        b = et_v7_bbox(r)
        if b is None:
            continue

        wr = (b[2]-b[0])/max(1,W)
        hr = (b[3]-b[1])/max(1,H)
        bottom = b[3]/max(1,H)
        cx = ((b[0]+b[2])/2)/max(1,W)

        crop = image_bgr[
            max(0,b[1]):min(H,b[3]),
            max(0,b[0]):min(W,b[2])
        ]

        if crop.size:
            gray = cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)
            edge = cv2.Canny(gray,80,180)
            dark = float(np.mean(gray < 180))
            edge_ratio = float(np.mean(edge > 0))
        else:
            dark = 0.0
            edge_ratio = 0.0

        # Side footer: tiny, bottom-edge, weak visual content.
        footer = (
            bottom >= 0.93
            and wr <= 0.11
            and hr <= 0.03
            and (cx <= 0.15 or cx >= 0.85)
            and dark <= 0.05
            and edge_ratio <= 0.07
        )

        if footer:
            removed.add(i)
            decisions["removed"].append({
                "index":i,
                "bbox":b,
                "reason":"PAGE_NUMBER_FOOTER",
            })

    # --------------------------------------------------------------------------------------------
    # D SECTION TITLE = nearest text above semantic content group
    # --------------------------------------------------------------------------------------------

    for group in groups:

        gy = group["bbox"][1]

        candidates = []

        for i,r in enumerate(expanded):

            if i in removed:
                continue

            b = et_v7_bbox(r)

            if b is None or b[3] > gy:
                continue

            wr = (b[2]-b[0])/max(1,W)
            hr = (b[3]-b[1])/max(1,H)
            gap = gy-b[3]

            if (
                wr >= 0.55
                and hr <= 0.045
                and 10 <= gap <= 35
            ):
                candidates.append((gap,i,b))

        if candidates:

            candidates.sort(key=lambda x:x[0])
            gap,i,b = candidates[0]

            expanded[i]["semantic_role"] = "SECTION_TITLE"
            expanded[i]["label"] = "SECTION_TITLE"
            expanded[i]["qg_eligible"] = False

            decisions["section_titles"].append({
                "index":i,
                "bbox":b,
                "following_group_bbox":group["bbox"],
                "gap":gap,
            })

    effective = [
        r for i,r in enumerate(expanded)
        if i not in removed
    ]

    for g in groups:
        decisions["content_groups"].append({
            "bbox":g["bbox"],
            "child_bboxes":g["child_bboxes"],
            "children_preserved":True,
            "group_semantic_only":True,
            "render_parent":False,
            "render_children":True,
            "coordinate_policy":"PRESERVE_CHILD_COMPONENT_COORDINATES",
        })

    return {
        "text_regions":effective,
        "content_groups":groups,
        "decisions":decisions,
    }

# ================================================================================================
# END P11 V7
# ================================================================================================



# ================================================================================================
# CUMULATIVE WORKING RULESET — GENERIC STRUCTURE / WHITESPACE REVISION
# Parent: P11_FULL_V7_ACCEPTED (immutable)
# This working source is cumulative; no page-coordinate hardcoding is used.
# ================================================================================================

_et_parent_examtrust_run_page = examtrust_run_page

_TERMINAL_RE = re.compile(r'[.!?。！？]\s*$')

def et_cw_bbox(x):
    b=x.get('bbox') or x.get('full_bbox') or x.get('core_bbox')
    return None if b is None else [int(round(float(v))) for v in b]

def et_cw_area(b):
    return max(0,b[2]-b[0])*max(0,b[3]-b[1])

def et_cw_inter(a,b):
    x1=max(a[0],b[0]); y1=max(a[1],b[1]); x2=min(a[2],b[2]); y2=min(a[3],b[3])
    return max(0,x2-x1)*max(0,y2-y1)

def et_cw_ocr(image,b):
    try:
        x1,y1,x2,y2=b
        crop=image[max(0,y1):max(y1+1,y2),max(0,x1):max(x1+1,x2)]
        if crop.size==0:return ''
        g=cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)
        g=cv2.resize(g,None,fx=2.2,fy=2.2,interpolation=cv2.INTER_CUBIC)
        return pytesseract.image_to_string(g,lang='vie+eng',config='--psm 7').strip() if _HAS_OCR else ''
    except Exception:
        return ''

def et_cw_line_inventory(image):
    lr=extract_whole_lines(image,exclusions=[])
    lines=[]
    for l in lr.get('whole_lines',[]):
        q=dict(l); q['ocr']=et_cw_ocr(image,q['bbox']); lines.append(q)
    return lines,lr.get('glyph_h_med',0.0)

def et_cw_is_marker_line(image,line):
    """Generic marker start: compact colored/icon component immediately left of aligned text."""
    H,W=image.shape[:2]; b=line['bbox']; y1,y2=max(0,b[1]-3),min(H,b[3]+3)
    x1=max(0,b[0]-28); x2=min(W,b[0]+8)
    crop=image[y1:y2,x1:x2]
    if crop.size==0:return False
    hsv=cv2.cvtColor(crop,cv2.COLOR_BGR2HSV)
    sat=float(np.mean(hsv[:,:,1]>80))
    return sat>=0.025

def et_cw_paragraph_regions(image, visual_exclusions):
    """Sentence-aware text flow. Whitespace is a candidate stop, not an unconditional stop."""
    H,W=image.shape[:2]
    lr=extract_whole_lines(image,exclusions=visual_exclusions)
    lines=lr.get('whole_lines',[])
    for l in lines:
        l['ocr']=et_cw_ocr(image,l['bbox'])
        l['is_structural_start']=_classify_line_signal(l['ocr'])
        l['is_marker_start']=et_cw_is_marker_line(image,l)
    if not lines:return []
    # Preserve engine column-band model, but paragraph stop uses semantic evidence.
    out=[]
    for band in _split_into_column_bands(lines,W):
        cur=[]
        for ln in band:
            if not cur: cur=[ln]; continue
            prev=cur[-1]
            gap=ln['bbox'][1]-prev['bbox'][3]
            prev_terminal=bool(_TERMINAL_RE.search((prev.get('ocr') or '').strip()))
            hard_start=bool(ln.get('is_structural_start') or ln.get('is_marker_start'))
            # Strong marker/structural signal always starts a new physical object.
            # Otherwise a whitespace gap can stop only after a terminal sentence boundary.
            stop = hard_start or (gap>max(5,1.4*max(1,lr.get('glyph_h_med',7))) and prev_terminal)
            if stop:
                b=union_box([x['bbox'] for x in cur])
                out.append({'bbox':b,'line_count':len(cur),'start_signal':cur[0].get('ocr','')[:60],
                            'stop_reason':'MARKER_OR_STRUCTURAL_START' if hard_start else 'TERMINAL_PUNCTUATION_NEWLINE',
                            'hold':False,'hold_reasons':[],'is_page_furniture':False})
                cur=[ln]
            else:
                cur.append(ln)
        if cur:
            b=union_box([x['bbox'] for x in cur])
            out.append({'bbox':b,'line_count':len(cur),'start_signal':cur[0].get('ocr','')[:60],
                        'stop_reason':'END_OF_BAND','hold':False,'hold_reasons':[],'is_page_furniture':False})
    return sorted(out,key=lambda r:(r['bbox'][1],r['bbox'][0]))

def et_cw_visual_duplicate_select(image, visuals, text_regions):
    """Same-visual proposals: reject oversized intruder; do not union geometry by default."""
    vs=[dict(v) for v in visuals]; boxes=[et_cw_bbox(v) for v in vs]
    n=len(vs); adj=[set() for _ in range(n)]
    for i in range(n):
        for j in range(i+1,n):
            inter=et_cw_inter(boxes[i],boxes[j])
            if inter/max(1,min(et_cw_area(boxes[i]),et_cw_area(boxes[j])))>=0.50:
                adj[i].add(j);adj[j].add(i)
    comps=[];seen=set()
    for i in range(n):
        if i in seen:continue
        st=[i];seen.add(i);cc=[]
        while st:
            k=st.pop();cc.append(k)
            for q in adj[k]:
                if q not in seen:seen.add(q);st.append(q)
        comps.append(cc)
    keep=[];dec=[]
    for cc in comps:
        if len(cc)==1:keep.append(vs[cc[0]]);continue
        scored=[]
        for i in cc:
            b=boxes[i]
            foreign=sum(et_cw_inter(b,et_cw_bbox(r)) for r in text_regions if et_cw_bbox(r))
            score=foreign/max(1,et_cw_area(b))
            scored.append((score,et_cw_area(b),-float(vs[i].get('confidence',0)),i))
        scored.sort(); ki=scored[0][3]
        keep.append(vs[ki])
        dec.append({'members':[boxes[i] for i in cc],'kept':boxes[ki],
                    'rejected':[boxes[i] for i in cc if i!=ki],
                    'rule':'SAME_VISUAL_REJECT_OVERSIZED_FOREIGN_CONTENT'})
    return keep,dec

def et_cw_footer_filter(image, regs):
    H,W=image.shape[:2]; out=[];removed=[]
    for r in regs:
        b=et_cw_bbox(r); wr=(b[2]-b[0])/W; hr=(b[3]-b[1])/H; cx=(b[0]+b[2])/(2*W)
        txt=et_cw_ocr(image,b).strip()
        footer=(b[3]/H>=.93 and wr<=.11 and hr<=.03 and (cx<=.15 or cx>=.85) and len(txt)<=3)
        if footer:removed.append({'bbox':b,'reason':'PAGE_NUMBER_FOOTER'})
        else:out.append(r)
    return out,removed

def et_cw_apply(image, base):
    """Cumulative generic pass; semantic parents are metadata-only."""
    # Preserve accepted P11 structural recovery first.
    raw_lines=extract_whole_lines(image,exclusions=[]).get('whole_lines',[])
    p11=et_v7_apply_structure(image,base['text_regions'],raw_lines)
    regs=list(p11['text_regions'])
    visuals=list(base['visual_boxes'])

    # 1) Duplicate visual proposals: select the least intrusive representative; never blind-union.
    visuals,vdec=et_cw_visual_duplicate_select(image,visuals,regs)

    # 2) Rebuild text from RAW after corrected visual exclusions.
    exclusions=[et_cw_bbox(v) for v in visuals if et_cw_bbox(v)]
    rebuilt=et_cw_paragraph_regions(image,exclusions)
    rebuilt,footer_removed=et_cw_footer_filter(image,rebuilt)

    # Conservative adoption: only use rebuilt regions if they are non-empty.
    # Existing title/fragment semantics are restored by downstream title/fragment classifiers in wrapper.
    if rebuilt:
        regs=rebuilt

    return regs,visuals,{
        'p11_structure':p11.get('decisions',{}),
        'visual_duplicate_decisions':vdec,
        'footer_removed':footer_removed,
        'rules':['ET-PHYSICAL-BOX-WHITESPACE-INVARIANT-V1',
                 'SAME_VISUAL_REJECT_OVERSIZED_FOREIGN_CONTENT',
                 'TERMINAL_PUNCTUATION_NEWLINE',
                 'MARKER_HARD_START_NO_BACKWARD_GROWTH']
    }

def examtrust_run_page(image_path,page_ref,prev_context=None,output_dir=None,save_outputs=True):
    base=_et_parent_examtrust_run_page(image_path,page_ref,prev_context,None,False)
    image=cv2.imread(str(image_path),cv2.IMREAD_COLOR)
    regs,visuals,cw=et_cw_apply(image,base)

    # Re-apply accepted text semantic classifiers to rebuilt text.
    H,W=image.shape[:2]
    regs,title_dec=files3_apply_text_title_labels(regs,W,H)
    regs,frag_dec=files3_apply_fragment_labels(regs,W,H)

    labels=build_labels(page_ref,regs,visuals,image,prev_context)
    rendered=render_page(image,regs,visuals,labels)
    review=rendered.copy()

    base['schema']='examtrust_one_full_cumulative_working'
    base['text_regions']=regs
    base['visual_boxes']=visuals
    base['labels']=labels
    base['cumulative_working']=cw
    base['text_title_decisions_cumulative']=title_dec
    base['fragment_decisions_cumulative']=frag_dec

    paths={}
    if save_outputs:
        if output_dir is None:raise ValueError('output_dir required when save_outputs=True')
        od=Path(output_dir);od.mkdir(parents=True,exist_ok=True)
        mp=od/f'{page_ref}_MANIFEST.json';rp=od/f'{page_ref}_RENDER.png';vp=od/f'{page_ref}_REVIEW.png'
        tmp=dict(base);tmp['output_paths']={}
        mp.write_text(json.dumps(tmp,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
        if not cv2.imwrite(str(rp),rendered):raise RuntimeError(str(rp))
        if not cv2.imwrite(str(vp),review):raise RuntimeError(str(vp))
        paths={'manifest':str(mp),'render':str(rp),'review':str(vp)}
    base['output_paths']=paths
    return base

def run_page(image_path,page_ref,prev_context=None,output_dir=None,save_outputs=True):
    return examtrust_run_page(image_path,page_ref,prev_context,output_dir,save_outputs)

def process_page(image_path,page_ref,prev_context=None,output_dir=None,save_outputs=True):
    return examtrust_run_page(image_path,page_ref,prev_context,output_dir,save_outputs)

def examtrust_cumulative_runner_version():
    return {'runner':'ONE_FULL_CUMULATIVE_WORKING','parent':'P11_FULL_V7_ACCEPTED',
            'parent_sha256':'14661710c0e005d6a6162d5c80c35f31153876bff4c1697c071893e36b310b65',
            'status':'WORKING_NOT_CHECKPOINTED'}

# ================================================================================================
# CUMULATIVE WORKING V2 — accepted P12 forensic corrections, generic implementation
# ================================================================================================

def et_cw2_compact_marker(image,line):
    H,W=image.shape[:2]; b=line['bbox']
    y1=max(0,b[1]-4); y2=min(H,b[3]+4); x1=max(0,b[0]-34); x2=min(W,b[0]+10)
    crop=image[y1:y2,x1:x2]
    if crop.size==0:return False
    hsv=cv2.cvtColor(crop,cv2.COLOR_BGR2HSV)
    m=((hsv[:,:,1]>=105)&(hsv[:,:,2]>=100)).astype(np.uint8)
    n,lab,stats,cent=cv2.connectedComponentsWithStats(m,8)
    for i in range(1,n):
        x,y,w,h,a=stats[i]
        if 8<=a<=180 and 4<=w<=18 and 5<=h<=20 and max(w/h,h/w)<=2.2:
            return True
    return False

# Replace the earlier permissive marker detector globally for the cumulative pass.
et_cw_is_marker_line = et_cw2_compact_marker

def et_cw2_duplicate_visual_select(image, visuals):
    """Transitive same-visual clustering; keep strongest complete seed, never union competing boxes."""
    vs=[dict(v) for v in visuals]; boxes=[et_cw_bbox(v) for v in vs]; n=len(vs)
    adj=[set() for _ in range(n)]
    for i in range(n):
        for j in range(i+1,n):
            inter=et_cw_inter(boxes[i],boxes[j])
            if inter/max(1,min(et_cw_area(boxes[i]),et_cw_area(boxes[j])))>=0.50:
                adj[i].add(j);adj[j].add(i)
    seen=set();out=[];dec=[]
    for i in range(n):
        if i in seen:continue
        st=[i];seen.add(i);cc=[]
        while st:
            k=st.pop();cc.append(k)
            for q in adj[k]:
                if q not in seen:seen.add(q);st.append(q)
        if len(cc)==1:
            out.append(vs[cc[0]]);continue
        # Complete seed: largest validated proposal in a same-visual cluster.
        # This avoids keeping a tiny nested crop and avoids blind union geometry.
        ki=max(cc,key=lambda q:(et_cw_area(boxes[q]),float(vs[q].get('confidence',0))))
        out.append(vs[ki])
        dec.append({'members':[boxes[q] for q in cc],'kept_seed':boxes[ki],
                    'rejected':[boxes[q] for q in cc if q!=ki],
                    'rule':'TRANSITIVE_SAME_VISUAL_KEEP_COMPLETE_SEED_NO_UNION'})
    return out,dec

def et_cw2_colored_semantic_containers(image):
    """Detect large thin colored borders; returns semantic containers only, never physical boxes."""
    H,W=image.shape[:2]; hsv=cv2.cvtColor(image,cv2.COLOR_BGR2HSV)
    m=((hsv[:,:,1]>=80)&(hsv[:,:,2]>=90)).astype(np.uint8)*255
    n,lab,stats,cent=cv2.connectedComponentsWithStats(m,8)
    out=[]
    for i in range(1,n):
        x,y,w,h,a=map(int,stats[i])
        if w/W>=.55 and h/H>=.16 and a/max(1,w*h)<=.08:
            out.append([x,y,x+w,y+h])
    return out

def et_cw2_runs(vals,pred,min_len=3,offset=0):
    out=[];s=None
    for i,v in enumerate(vals):
        if pred(v):
            if s is None:s=i
        else:
            if s is not None and i-s>=min_len:out.append((offset+s,offset+i-1,i-s))
            s=None
    if s is not None and len(vals)-s>=min_len:out.append((offset+s,offset+len(vals)-1,len(vals)-s))
    return out

def et_cw2_visual_island_in_container(image,container):
    """Find a right-side visual island separated from left text by a real whitespace corridor.
    The island includes its internal labels/caption and stops at the first outer whitespace moat.
    """
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY); dark=gray<220
    x1,y1,x2,y2=container; w=x2-x1; h=y2-y1
    # Ignore border/header strip and bottom border while finding the lane corridor.
    ya=y1+max(18,int(.10*h)); yb=y1+int(.80*h)
    if yb<=ya:return None
    col=dark[ya:yb,x1:x2].sum(axis=0)
    corridors=et_cw2_runs(col,lambda v:v<=2,min_len=max(5,int(.012*w)),offset=x1)
    # interior corridor near middle; border whitespace is ignored
    corridors=[r for r in corridors if x1+.30*w<=((r[0]+r[1])/2)<=x1+.72*w]
    if not corridors:return None
    c=max(corridors,key=lambda r:r[2]); split=(c[0]+c[1])//2
    # Right outer moat: whitespace run between island and semantic border.
    right_col=dark[ya:yb,split:x2].sum(axis=0)
    rr=et_cw2_runs(right_col,lambda v:v<=2,min_len=5,offset=split)
    rr=[r for r in rr if r[0]>split+15]
    right=(rr[-1][0]+rr[-1][1])//2 if rr else x2-3
    # Row projection in right lane. First ink after header; first stable moat after the main island
    row=dark[y1+5:y2-3,split:right].sum(axis=1)
    # content rows with meaningful ink, avoiding border/header colored rule
    idx=np.where(row>=3)[0]
    if len(idx)==0:return None
    top0=y1+5+int(idx[0])
    # avoid semantic header: require a sustained content run below top 7% of container
    search_start=max(top0,y1+int(.08*h))
    rs=dark[search_start:y2-3,split:right].sum(axis=1)
    ink=np.where(rs>=3)[0]
    if len(ink)==0:return None
    top=search_start+int(ink[0])
    # choose first >=5-row whitespace moat after at least 35% container height of island opportunity
    moats=et_cw2_runs(rs,lambda v:v<=2,min_len=5,offset=search_start)
    moats=[r for r in moats if r[0]>=top+int(.25*h)]
    if not moats:return None
    bottom_moat=moats[0]
    bottom=(bottom_moat[0]+bottom_moat[1])//2
    # Top boundary at nearest whitespace immediately above first content.
    pre=dark[y1:top,split:right].sum(axis=1)
    pre_runs=et_cw2_runs(pre,lambda v:v<=2,min_len=3,offset=y1)
    pre_runs=[r for r in pre_runs if r[1]<top]
    topb=(pre_runs[-1][0]+pre_runs[-1][1])//2 if pre_runs else max(y1+2,top-2)
    # Physical edges placed in whitespace corridor/moats.
    left=(c[0]+c[1])//2
    return [int(left),int(topb),int(right),int(bottom)]

def et_cw2_false_shallow_visual(image,v,containers):
    b=et_cw_bbox(v); H,W=image.shape[:2]
    hr=(b[3]-b[1])/H; wr=(b[2]-b[0])/W
    # A shallow strip crossing the bottom of a bordered semantic container is not a standalone visual.
    for c in containers:
        if c[0]<=b[0]<=c[2] and c[1]<=b[1]<=c[3] and hr<=.045 and wr>=.25 and b[1]>=c[1]+.70*(c[3]-c[1]):
            return True
    return False

def et_cw2_apply(image,base):
    # accepted P11 recovery stays first
    raw_lines=extract_whole_lines(image,exclusions=[]).get('whole_lines',[])
    p11=et_v7_apply_structure(image,base['text_regions'],raw_lines)
    base_regs=list(p11['text_regions'])
    visuals,vdec=et_cw2_duplicate_visual_select(image,list(base['visual_boxes']))
    containers=et_cw2_colored_semantic_containers(image)

    # Reject false shallow strips before text extraction.
    kept=[];vrej=[]
    for v in visuals:
        if et_cw2_false_shallow_visual(image,v,containers):
            vrej.append({'bbox':et_cw_bbox(v),'reason':'SHALLOW_STRIP_INSIDE_SEMANTIC_CONTAINER'})
        else:kept.append(v)
    visuals=kept

    # Recover visual islands inside semantic bordered containers from RAW whitespace geometry.
    recovered=[]
    for c in containers:
        vb=et_cw2_visual_island_in_container(image,c)
        if vb is None:continue
        # require substantial non-white content and avoid duplicating an existing visual
        crop=cv2.cvtColor(image[vb[1]:vb[3],vb[0]:vb[2]],cv2.COLOR_BGR2GRAY)
        if crop.size==0 or float(np.mean(crop<235))<.025:continue
        if any(et_cw_inter(vb,et_cw_bbox(v))/max(1,min(et_cw_area(vb),et_cw_area(et_cw_bbox(v))))>.45 for v in visuals):continue
        recovered.append({'core_bbox':vb,'full_bbox':vb,'caption_lines':[],
                          'confidence':0.90,'semantic_role':'VISUAL',
                          'recovery_rule':'SEMANTIC_CONTAINER_WHITESPACE_ISLAND'})
    visuals.extend(recovered)

    exclusions=[et_cw_bbox(v) for v in visuals if et_cw_bbox(v)]
    regs=et_cw_paragraph_regions(image,exclusions)
    regs,footer_removed=et_cw_footer_filter(image,regs)
    return regs,visuals,{
        'p11_structure':p11.get('decisions',{}),'visual_duplicate_decisions':vdec,
        'semantic_containers':[{'bbox':c,'render_parent':False,'group_semantic_only':True} for c in containers],
        'visual_recovered':[et_cw_bbox(v) for v in recovered],'visual_rejected':vrej,
        'footer_removed':footer_removed,
        'rules':['ET-PHYSICAL-BOX-WHITESPACE-INVARIANT-V1','TRANSITIVE_SAME_VISUAL_KEEP_COMPLETE_SEED_NO_UNION',
                 'MARKER_COMPACT_ICON_HARD_START','SEMANTIC_BORDER_METADATA_ONLY',
                 'SEMANTIC_CONTAINER_WHITESPACE_VISUAL_ISLAND','SHALLOW_FALSE_VISUAL_REJECTION',
                 'TERMINAL_PUNCTUATION_NEWLINE']}

# Replace only the cumulative application layer; runner remains one full cumulative runner.
et_cw_apply = et_cw2_apply

# ================================================================================================
# CUMULATIVE WORKING V3 — flow reconstruction around whitespace-locked visuals
# ================================================================================================
_LIST_ITEM_RE = re.compile(r'^\s*(?:[QA]|[A-Z])\s*[<>≤≥=]\s*[-+]?\s*\d',re.I)

def et_cw3_is_list_item(txt):
    t=(txt or '').strip().replace('Ú','0').replace('O','0')
    return bool(_LIST_ITEM_RE.search(t))

def et_cw3_union_lines(lines):
    return union_box([l['bbox'] for l in lines])

def et_cw3_text_record(lines,reason,role='TEXT'):
    return {'bbox':et_cw3_union_lines(lines),'line_count':len(lines),
            'start_signal':(lines[0].get('ocr') or '')[:80], 'stop_reason':reason,
            'hold':False,'hold_reasons':[],'is_page_furniture':False,
            'semantic_role':role,'label':role,'qg_eligible':role=='TEXT'}

def et_cw3_reconstruct_neighbor_flow(image, visual, all_lines):
    """Reconstruct text immediately before/left of a visual from RAW whole-lines.
    Full-width text above the visual is allowed; while vertically overlapping the visual,
    only the whitespace-separated left lane is accepted. Marker/icon is a hard new object.
    """
    vb=et_cw_bbox(visual); H,W=image.shape[:2]
    vx1,vy1,vx2,vy2=vb
    ya=max(0,vy1-int(.06*H)); yb=min(H,vy2+int(.04*H))
    cand=[]
    for l in all_lines:
        b=l['bbox']; cy=(b[1]+b[3])/2
        if not (ya<=cy<=yb):continue
        # exclude visual-owned lines while overlapping visual vertically
        if b[1] < vy2 and b[3] > vy1:
            hov=max(0,min(b[2],vx2)-max(b[0],vx1))/max(1,b[2]-b[0])
            if hov>.10:continue
        # once alongside visual, line must remain on left side of whitespace corridor
        if b[1]>=vy1 and b[0]>=vx1:continue
        q=dict(l);q['ocr']=et_cw_ocr(image,b);q['marker']=et_cw2_compact_marker(image,q)
        cand.append(q)
    cand=sorted(cand,key=lambda z:(z['bbox'][1],z['bbox'][0]))
    if not cand:return []
    out=[];cur=[];list_mode=False
    for ln in cand:
        txt=(ln.get('ocr') or '').strip()
        if ln['marker']:
            if cur:out.append(et_cw3_text_record(cur,'MARKER_HARD_START'));cur=[]
            out.append(et_cw3_text_record([ln],'MARKER_OBJECT','MARKER_TEXT'));list_mode=False
            continue
        if not cur:
            cur=[ln]; list_mode=txt.endswith(':'); continue
        prev=cur[-1]; ptxt=(prev.get('ocr') or '').strip()
        # Header ending ':' followed by symbolic/list items establishes list mode.
        if (ptxt.endswith(':') and et_cw3_is_list_item(txt)) or (list_mode and et_cw3_is_list_item(txt)):
            cur.append(ln);list_mode=True;continue
        # In list mode, retain list items despite terminal periods; stop before non-list/marker.
        if list_mode and not et_cw3_is_list_item(txt):
            out.append(et_cw3_text_record(cur,'END_OF_LIST_BLOCK'));cur=[ln];list_mode=txt.endswith(':');continue
        # Ordinary paragraph: terminal punctuation + newline starts next object.
        if _TERMINAL_RE.search(ptxt):
            out.append(et_cw3_text_record(cur,'TERMINAL_PUNCTUATION_NEWLINE'));cur=[ln];list_mode=txt.endswith(':')
        else:
            cur.append(ln)
    if cur:out.append(et_cw3_text_record(cur,'END_OF_NEIGHBOR_FLOW'))
    return out

def et_cw3_container_text_flow(image,container,visual,all_lines):
    """Semantic-border flow: left text while beside visual, full-width text after visual bottom.
    Visual-owned internal labels are excluded by the visual physical box.
    """
    c=container; vb=et_cw_bbox(visual); x1,y1,x2,y2=c
    lines=[]
    for l in all_lines:
        b=l['bbox'];cx=(b[0]+b[2])/2;cy=(b[1]+b[3])/2
        if not (x1<cx<x2 and y1<cy<y2):continue
        # visual-owned content is not text
        inter=et_cw_inter(b,vb)
        if inter/max(1,et_cw_area(b))>.15:continue
        # while beside visual, retain only left lane; below visual, release to full width
        if b[1] < vb[3] and b[3] > vb[1] and b[2] > vb[0]:continue
        q=dict(l);q['ocr']=et_cw_ocr(image,b);q['marker']=et_cw2_compact_marker(image,q);lines.append(q)
    lines=sorted(lines,key=lambda z:(z['bbox'][1],z['bbox'][0]))
    # Remove semantic border/header colored strokes and tiny artifacts.
    lines=[l for l in lines if (l['bbox'][2]-l['bbox'][0])>=18 and (l['bbox'][3]-l['bbox'][1])>=5]
    if not lines:return []
    out=[];cur=[]
    for ln in lines:
        txt=(ln.get('ocr') or '').strip()
        if ln['marker']:
            if cur:out.append(et_cw3_text_record(cur,'MARKER_HARD_START'));cur=[]
            out.append(et_cw3_text_record([ln],'MARKER_OBJECT','MARKER_TEXT'));continue
        if not cur:cur=[ln];continue
        prev=cur[-1];pt=(prev.get('ocr') or '').strip()
        # New paragraph only after a completed sentence; geometry gap alone never forces stop.
        if _TERMINAL_RE.search(pt):
            out.append(et_cw3_text_record(cur,'TERMINAL_PUNCTUATION_NEWLINE'));cur=[ln]
        else:cur.append(ln)
    if cur:out.append(et_cw3_text_record(cur,'END_OF_CONTAINER_FLOW'))
    return out

def et_cw3_apply(image,base):
    raw=extract_whole_lines(image,exclusions=[]).get('whole_lines',[])
    p11=et_v7_apply_structure(image,base['text_regions'],raw)
    parent_regs=list(p11['text_regions'])
    visuals,vdec=et_cw2_duplicate_visual_select(image,list(base['visual_boxes']))
    containers=et_cw2_colored_semantic_containers(image)
    # false shallow visual rejection
    vv=[];vrej=[]
    for v in visuals:
        if et_cw2_false_shallow_visual(image,v,containers):vrej.append({'bbox':et_cw_bbox(v),'reason':'SHALLOW_STRIP_INSIDE_SEMANTIC_CONTAINER'})
        else:vv.append(v)
    visuals=vv
    # recover one whitespace island per semantic container where present
    recovered=[]
    for c in containers:
        vb=et_cw2_visual_island_in_container(image,c)
        if vb:
            rec={'core_bbox':vb,'full_bbox':vb,'caption_lines':[],'confidence':.90,'semantic_role':'VISUAL','recovery_rule':'SEMANTIC_CONTAINER_WHITESPACE_ISLAND'}
            recovered.append(rec);visuals.append(rec)

    # OCR once for flow decisions
    all_lines=[]
    for l in raw:
        q=dict(l);q['ocr']=et_cw_ocr(image,q['bbox']);all_lines.append(q)

    regs=list(parent_regs)
    replacements=[]
    # For visuals outside semantic containers, rebuild only their neighboring flow envelope.
    for v in visuals:
        vb=et_cw_bbox(v)
        inside_c=next((c for c in containers if c[0]<=((vb[0]+vb[2])/2)<=c[2] and c[1]<=((vb[1]+vb[3])/2)<=c[3]),None)
        if inside_c:continue
        rr=et_cw3_reconstruct_neighbor_flow(image,v,all_lines)
        if not rr:continue
        env=[min(r['bbox'][0] for r in rr),min(r['bbox'][1] for r in rr),max(r['bbox'][2] for r in rr),max(r['bbox'][3] for r in rr)]
        regs=[r for r in regs if et_cw_inter(et_cw_bbox(r),env)/max(1,et_cw_area(et_cw_bbox(r)))<.20]
        regs.extend(rr);replacements.append({'type':'VISUAL_NEIGHBOR_FLOW','visual':vb,'regions':[r['bbox'] for r in rr]})
    # Semantic container content is rebuilt as a unit; parent border remains metadata only.
    for c in containers:
        rv=next((v for v in recovered if c[0]<=((et_cw_bbox(v)[0]+et_cw_bbox(v)[2])/2)<=c[2]),None)
        if rv is None:continue
        rr=et_cw3_container_text_flow(image,c,rv,all_lines)
        regs=[r for r in regs if not (c[0] <= (et_cw_bbox(r)[0]+et_cw_bbox(r)[2])/2 <= c[2] and c[1] <= (et_cw_bbox(r)[1]+et_cw_bbox(r)[3])/2 <= c[3])]
        regs.extend(rr);replacements.append({'type':'SEMANTIC_CONTAINER_FLOW','container':c,'regions':[r['bbox'] for r in rr]})
    regs,footer_removed=et_cw_footer_filter(image,regs)
    regs=sorted(regs,key=lambda r:(r['bbox'][1],r['bbox'][0]))
    return regs,visuals,{
      'p11_structure':p11.get('decisions',{}),'visual_duplicate_decisions':vdec,
      'semantic_containers':[{'bbox':c,'render_parent':False,'group_semantic_only':True} for c in containers],
      'visual_recovered':[et_cw_bbox(v) for v in recovered],'visual_rejected':vrej,
      'flow_replacements':replacements,'footer_removed':footer_removed,
      'rules':['ET-PHYSICAL-BOX-WHITESPACE-INVARIANT-V1','TRANSITIVE_SAME_VISUAL_KEEP_COMPLETE_SEED_NO_UNION',
               'MARKER_COMPACT_ICON_HARD_START','TERMINAL_PUNCTUATION_NEWLINE','LIST_BLOCK_CONTINUATION',
               'SEMANTIC_BORDER_METADATA_ONLY','SEMANTIC_CONTAINER_WHITESPACE_VISUAL_ISLAND','WRAP_AROUND_VISUAL_FLOW']}

et_cw_apply=et_cw3_apply

# ================================================================================================
# CUMULATIVE WORKING V4 — formula merge + left-neighbor guard + outer whitespace for visual seed
# ================================================================================================

def et_cw4_expand_visual_vertical_to_moat(image,v):
    n=dict(v); b=et_cw_bbox(n); gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY); dark=gray<220
    H,W=gray.shape[:2]; x1,y1,x2,y2=b
    # nearest stable horizontal whitespace run immediately above/below the seed.
    def nearest_above():
        vals=dark[max(0,y1-30):y1,max(0,x1-8):min(W,x2+3)].sum(axis=1)
        rr=et_cw2_runs(vals,lambda z:z<=2,3,max(0,y1-30))
        return (rr[-1][0]+rr[-1][1])//2 if rr else y1
    def nearest_below():
        vals=dark[y2:min(H,y2+30),max(0,x1-8):min(W,x2+3)].sum(axis=1)
        rr=et_cw2_runs(vals,lambda z:z<=2,3,y2)
        return (rr[0][0]+rr[0][1])//2 if rr else y2
    nb=[x1,nearest_above(),x2,nearest_below()]
    n['core_bbox']=nb;n['full_bbox']=nb;n['boundary_rule']='NEAREST_OUTER_HORIZONTAL_WHITESPACE_MOAT'
    return n

def et_cw4_merge_formula_parts(regs,glyph):
    regs=[dict(r) for r in regs];used=set();out=[];dec=[]
    for i,a in enumerate(regs):
        if i in used:continue
        A=et_cw_bbox(a);cand=None
        if a.get('line_count')==1 and (A[3]-A[1])<=max(14,2.2*glyph):
            for j in range(i+1,len(regs)):
                if j in used:continue
                b=regs[j];B=et_cw_bbox(b)
                if b.get('line_count')!=1 or (B[3]-B[1])>max(14,2.2*glyph):continue
                gap=B[0]-A[2]; inter_y=max(0,min(A[3],B[3])-max(A[1],B[1])); vov=inter_y/max(1,min(A[3]-A[1],B[3]-B[1]))
                if vov>=.80 and 0<=gap<=max(80,12*glyph) and (A[2]-A[0])<=90 and (B[2]-B[0])<=90:
                    cand=(j,b,B);break
        if cand:
            j,b,B=cand;n=dict(a);n['bbox']=union_box([A,B]);n['line_count']=1;n['semantic_role']='FORMULA';n['label']='FORMULA';n['qg_eligible']=True
            n['formula_children']=[A,B];n['formula_merge_rule']='SAME_BASELINE_SHORT_COMPONENTS'
            out.append(n);used|={i,j};dec.append({'children':[A,B],'bbox':n['bbox']})
        else:out.append(a);used.add(i)
    return sorted(out,key=lambda r:(r['bbox'][1],r['bbox'][0])),dec

# tighten neighbor flow: it reconstructs only the text lane left of the visual.
_et_cw3_neighbor_original=et_cw3_reconstruct_neighbor_flow
def et_cw4_reconstruct_neighbor_flow(image,visual,all_lines):
    rr=_et_cw3_neighbor_original(image,visual,all_lines); vx1=et_cw_bbox(visual)[0]
    return [r for r in rr if r['bbox'][0] < vx1 and (r['bbox'][0]+r['bbox'][2])/2 < vx1]
et_cw3_reconstruct_neighbor_flow=et_cw4_reconstruct_neighbor_flow

_et_cw3_apply_original=et_cw3_apply
def et_cw4_apply(image,base):
    regs,visuals,cw=_et_cw3_apply_original(image,base)
    # Expand non-container visual seed vertically to outer whitespace so body/caption are not clipped.
    containers=[x['bbox'] for x in cw.get('semantic_containers',[])]
    vv=[]
    for v in visuals:
        b=et_cw_bbox(v);cx=(b[0]+b[2])/2;cy=(b[1]+b[3])/2
        inside=any(c[0]<=cx<=c[2] and c[1]<=cy<=c[3] for c in containers)
        vv.append(v if inside else et_cw4_expand_visual_vertical_to_moat(image,v))
    visuals=vv
    glyph=extract_whole_lines(image,exclusions=[]).get('glyph_h_med',7)
    regs,fm=et_cw4_merge_formula_parts(regs,glyph)
    cw['formula_merges']=fm;cw['rules']=cw.get('rules',[])+['FORMULA_SAME_BASELINE_COMPONENT_MERGE','VISUAL_OUTER_WHITESPACE_MOAT']
    return regs,visuals,cw
et_cw_apply=et_cw4_apply

# ================================================================================================
# CUMULATIVE WORKING V5 — resolve cross-lane text overlap by real whitespace corridor
# ================================================================================================

def et_cw5_split_overlapping_lanes(image,regs,glyph):
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY);dark=gray<220
    out=[dict(r) for r in regs];dec=[]
    for i in range(len(out)):
        A=out[i]['bbox']
        for j in range(i+1,len(out)):
            B=out[j]['bbox']
            iy1=max(A[1],B[1]);iy2=min(A[3],B[3])
            if iy2-iy1 < max(12,2*glyph):continue
            # candidate side-by-side regions currently overlap only around lane boundary
            if not (A[0] < B[0] and A[2] > B[0] and A[2] <= B[2]):continue
            if (A[2]-B[0]) > .18*min(A[2]-A[0],B[2]-B[0]):continue
            ux1=max(A[0],min(A[2],B[0])-max(40,int(8*glyph)));ux2=min(B[2],max(A[2],B[0])+max(40,int(8*glyph)))
            vals=dark[iy1:iy2,ux1:ux2].sum(axis=0)
            runs=et_cw2_runs(vals,lambda z:z<=1,min_len=max(5,int(1.5*glyph)),offset=ux1)
            # corridor must lie between the content centroids, not at outer margins
            runs=[r for r in runs if A[0]+.45*(A[2]-A[0]) < (r[0]+r[1])/2 < B[0]+.55*(B[2]-B[0])]
            if not runs:continue
            c=max(runs,key=lambda r:r[2]);mid=(c[0]+c[1])//2
            oldA=list(A);oldB=list(B)
            A[2]=min(A[2],mid);B[0]=max(B[0],mid)
            out[i]['bbox']=A;out[j]['bbox']=B
            dec.append({'left_before':oldA,'right_before':oldB,'corridor':[c[0],c[1]],'split_x':mid,
                        'left_after':list(A),'right_after':list(B),'rule':'REAL_WHITESPACE_CORRIDOR'})
    return out,dec

_et_cw4_apply_original=et_cw4_apply
def et_cw5_apply(image,base):
    regs,visuals,cw=_et_cw4_apply_original(image,base)
    glyph=extract_whole_lines(image,exclusions=[]).get('glyph_h_med',7)
    regs,ld=et_cw5_split_overlapping_lanes(image,regs,glyph)
    cw['lane_corridor_splits']=ld;cw['rules']=cw.get('rules',[])+['REAL_WHITESPACE_CORRIDOR_LANE_SPLIT']
    return regs,visuals,cw
et_cw_apply=et_cw5_apply

# ================================================================================================
# CUMULATIVE WORKING V6 — symmetric lane corridor split
# ================================================================================================
def et_cw6_split_overlapping_lanes(image,regs,glyph):
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY);dark=gray<220
    out=[dict(r) for r in regs];dec=[]
    for i in range(len(out)):
        for j in range(i+1,len(out)):
            A=out[i]['bbox'];B=out[j]['bbox']; iy1=max(A[1],B[1]);iy2=min(A[3],B[3])
            if iy2-iy1 < max(12,2*glyph):continue
            # Determine left/right by x origin, independent of reading-order index.
            li,ri=(i,j) if A[0]<=B[0] else (j,i); L=out[li]['bbox'];R=out[ri]['bbox']
            if not (L[2]>R[0]):continue
            if (L[2]-R[0]) > .18*min(L[2]-L[0],R[2]-R[0]):continue
            ux1=max(L[0],min(L[2],R[0])-max(40,int(8*glyph)));ux2=min(R[2],max(L[2],R[0])+max(40,int(8*glyph)))
            vals=dark[iy1:iy2,ux1:ux2].sum(axis=0)
            runs=et_cw2_runs(vals,lambda z:z<=1,min_len=max(5,int(1.5*glyph)),offset=ux1)
            runs=[r for r in runs if L[0]+.45*(L[2]-L[0]) < (r[0]+r[1])/2 < R[0]+.55*(R[2]-R[0])]
            if not runs:continue
            c=max(runs,key=lambda r:r[2]);mid=(c[0]+c[1])//2;oldL=list(L);oldR=list(R)
            L[2]=min(L[2],mid);R[0]=max(R[0],mid);out[li]['bbox']=L;out[ri]['bbox']=R
            dec.append({'left_before':oldL,'right_before':oldR,'corridor':[c[0],c[1]],'split_x':mid,
                        'left_after':list(L),'right_after':list(R),'rule':'REAL_WHITESPACE_CORRIDOR'})
    return out,dec

_et_cw5_apply_original=et_cw5_apply
def et_cw6_apply(image,base):
    regs,visuals,cw=_et_cw5_apply_original(image,base)
    glyph=extract_whole_lines(image,exclusions=[]).get('glyph_h_med',7)
    regs,ld=et_cw6_split_overlapping_lanes(image,regs,glyph)
    # V5 attempted no effective split on reversed reading order; replace its empty diagnostics.
    cw['lane_corridor_splits']=ld;cw['rules']=cw.get('rules',[])+['SYMMETRIC_REAL_WHITESPACE_CORRIDOR']
    return regs,visuals,cw
et_cw_apply=et_cw6_apply

# ================================================================================================
# CUMULATIVE WORKING V7 — wrap-around text physical children, semantic parent metadata only
# ================================================================================================
def et_cw7_resolve_text_visual_wrap(image,regs,visuals):
    raw=extract_whole_lines(image,exclusions=[]).get('whole_lines',[]);out=[];groups=[];dec=[]
    for r in regs:
        rb=et_cw_bbox(r);hit=None
        for v in visuals:
            vb=et_cw_bbox(v)
            if et_cw_inter(rb,vb)>0:hit=vb;break
        if hit is None:
            out.append(r);continue
        # recover whole-lines whose centers belong to this text region
        ins=[]
        for l in raw:
            b=l['bbox'];cx=(b[0]+b[2])/2;cy=(b[1]+b[3])/2
            if rb[0]<=cx<=rb[2] and rb[1]<=cy<=rb[3]:ins.append(l)
        if not ins:
            out.append(r);continue
        top=[];side=[];bad=[]
        for l in ins:
            b=l['bbox']
            if b[3] <= hit[1]:top.append(l)
            elif b[2] <= hit[0]:side.append(l)
            else:bad.append(l)
        # only split when every text line can be placed without touching visual.
        if bad or not top or not side:
            out.append(r);continue
        children=[]
        for chunk,role in ((top,'WRAP_TOP'),(side,'WRAP_SIDE')):
            n=dict(r);n['bbox']=union_box([l['bbox'] for l in chunk]);n['line_count']=len(chunk)
            n['wrap_child_role']=role;n['semantic_role']='TEXT';n['label']='TEXT';children.append(n);out.append(n)
        parent=union_box([c['bbox'] for c in children])
        groups.append({'type':'WRAP_AROUND_TEXT_GROUP','parent_bbox':parent,
                       'children':[c['bbox'] for c in children],'group_semantic_only':True,
                       'render_parent':False,'render_children':True,'coordinate_policy':'PRESERVE_CHILD_COMPONENT_COORDINATES'})
        dec.append({'source_bbox':rb,'visual_bbox':hit,'children':[c['bbox'] for c in children],
                    'rule':'TEXT_WRAP_AROUND_VISUAL_PHYSICAL_CHILDREN'})
    return sorted(out,key=lambda r:(r['bbox'][1],r['bbox'][0])),groups,dec

_et_cw6_apply_original=et_cw6_apply
def et_cw7_apply(image,base):
    regs,visuals,cw=_et_cw6_apply_original(image,base)
    regs,groups,dec=et_cw7_resolve_text_visual_wrap(image,regs,visuals)
    cw['wrap_text_groups']=groups;cw['wrap_text_decisions']=dec
    cw['rules']=cw.get('rules',[])+['TEXT_WRAP_AROUND_VISUAL_PHYSICAL_CHILDREN']
    return regs,visuals,cw
et_cw_apply=et_cw7_apply

# ================================================================================================
# CUMULATIVE WORKING V8 — paragraph continuity inside a semantic container
# Generic correction: terminal punctuation alone is NOT a paragraph boundary.
# Adjacent same-lane physical text chunks are rejoined when whitespace/indent evidence says
# the reading block continues. Marker/icon hard-start remains a hard boundary.
# ================================================================================================

def et_cw8_merge_continuous_text_blocks(image, regs, visuals, cw):
    containers=[x['bbox'] for x in cw.get('semantic_containers',[]) if x.get('bbox')]
    if not containers:return regs,[]
    out=list(regs); decisions=[]
    for c in containers:
        inside=[r for r in out if c[0] <= (et_cw_bbox(r)[0]+et_cw_bbox(r)[2])/2 <= c[2]
                              and c[1] <= (et_cw_bbox(r)[1]+et_cw_bbox(r)[3])/2 <= c[3]
                              and r.get('semantic_role')!='MARKER_TEXT']
        inside=sorted(inside,key=lambda r:(et_cw_bbox(r)[1],et_cw_bbox(r)[0]))
        if len(inside)<2:continue
        used=set(); merged=[]
        for i,a in enumerate(inside):
            if i in used:continue
            ab=et_cw_bbox(a); chain=[a]
            for j in range(i+1,len(inside)):
                if j in used:continue
                b=inside[j]; bb=et_cw_bbox(b)
                # same physical lane, small inter-block whitespace, compatible left edge.
                gap=bb[1]-et_cw_bbox(chain[-1])[3]
                left_delta=abs(bb[0]-et_cw_bbox(chain[-1])[0])
                xov=max(0,min(ab[2],bb[2])-max(ab[0],bb[0]))
                same_lane=(left_delta<=18 and xov>=.45*min(ab[2]-ab[0],bb[2]-bb[0]))
                # Never bridge across a visual vertically/horizontally.
                bridge=[min(et_cw_bbox(chain[-1])[0],bb[0]),et_cw_bbox(chain[-1])[3],max(et_cw_bbox(chain[-1])[2],bb[2]),bb[1]]
                visual_block=any(et_cw_inter(bridge,et_cw_bbox(v))>0 for v in visuals)
                if 0 <= gap <= 8 and same_lane and not visual_block:
                    chain.append(b);used.add(j);ab=union_box([et_cw_bbox(x) for x in chain])
                else:
                    # reading order has moved beyond this lane
                    if bb[1] > et_cw_bbox(chain[-1])[3]+8:break
            if len(chain)>1:
                n=dict(chain[0]);n['bbox']=union_box([et_cw_bbox(x) for x in chain])
                n['line_count']=sum(int(x.get('line_count',1) or 1) for x in chain)
                n['stop_reason']=chain[-1].get('stop_reason','PARAGRAPH_CONTINUATION')
                n['paragraph_continuity_rule']='SAME_LANE_SMALL_GAP_NO_MARKER_NO_VISUAL'
                merged.append(n);used.add(i)
                decisions.append({'source_boxes':[et_cw_bbox(x) for x in chain],'merged_bbox':n['bbox'],
                                  'rule':'TERMINAL_PUNCTUATION_ALONE_DOES_NOT_SPLIT_PARAGRAPH'})
            else:
                merged.append(a);used.add(i)
        ids={id(r) for r in inside}
        out=[r for r in out if id(r) not in ids]+merged
    return sorted(out,key=lambda r:(r['bbox'][1],r['bbox'][0])),decisions

_et_cw7_apply_original=et_cw7_apply
def et_cw8_apply(image,base):
    regs,visuals,cw=_et_cw7_apply_original(image,base)
    regs,dec=et_cw8_merge_continuous_text_blocks(image,regs,visuals,cw)
    cw['paragraph_continuity_decisions']=dec
    cw['rules']=cw.get('rules',[])+['TERMINAL_PUNCTUATION_ALONE_NOT_PARAGRAPH_STOP']
    return regs,visuals,cw
et_cw_apply=et_cw8_apply

# ================================================================================================
# CUMULATIVE WORKING V9 — unfinished-sentence continuation across adjacent physical text chunks
# Generic: if the last RAW line of a text chunk has no terminal punctuation, a small whitespace
# gap cannot terminate it. Merge the next same-lane text chunk unless a marker/visual intervenes.
# ================================================================================================

def et_cw9_last_line_text(image,bbox):
    lines=extract_whole_lines(image,exclusions=[]).get('whole_lines',[])
    ins=[]
    for l in lines:
        b=l['bbox'];cx=(b[0]+b[2])/2;cy=(b[1]+b[3])/2
        if bbox[0]<=cx<=bbox[2] and bbox[1]-2<=cy<=bbox[3]+2:ins.append(l)
    if not ins:return ''
    l=max(ins,key=lambda z:z['bbox'][1])
    return (et_cw_ocr(image,l['bbox']) or '').strip()

def et_cw9_merge_unfinished_sentence(image,regs,visuals):
    regs=sorted(regs,key=lambda r:(et_cw_bbox(r)[1],et_cw_bbox(r)[0]));out=[];dec=[];i=0
    while i<len(regs):
        a=regs[i]
        if i+1>=len(regs) or a.get('semantic_role') in ('TITLE','FORMULA','MARKER_TEXT'):
            out.append(a);i+=1;continue
        b=regs[i+1]
        if b.get('semantic_role') in ('TITLE','FORMULA','MARKER_TEXT'):
            out.append(a);i+=1;continue
        ab=et_cw_bbox(a);bb=et_cw_bbox(b);gap=bb[1]-ab[3]
        left_delta=abs(bb[0]-ab[0]); xov=max(0,min(ab[2],bb[2])-max(ab[0],bb[0]))
        same_lane=left_delta<=18 and xov>=.45*min(ab[2]-ab[0],bb[2]-bb[0])
        last=et_cw9_last_line_text(image,ab)
        unfinished=not bool(_TERMINAL_RE.search(last))
        bridge=[min(ab[0],bb[0]),ab[3],max(ab[2],bb[2]),bb[1]]
        visual_block=any(et_cw_inter(bridge,et_cw_bbox(v))>0 for v in visuals)
        if 0<=gap<=5 and same_lane and unfinished and not visual_block:
            n=dict(a);n['bbox']=union_box([ab,bb]);n['line_count']=int(a.get('line_count',1) or 1)+int(b.get('line_count',1) or 1)
            n['stop_reason']=b.get('stop_reason','UNFINISHED_SENTENCE_CONTINUATION')
            n['paragraph_continuity_rule']='UNFINISHED_SENTENCE_SMALL_GAP_SAME_LANE'
            out.append(n);dec.append({'source_boxes':[ab,bb],'merged_bbox':n['bbox'],'last_line_ocr':last,
                                      'rule':'UNFINISHED_SENTENCE_CANNOT_STOP_ON_SMALL_WHITESPACE'})
            i+=2
        else:
            out.append(a);i+=1
    return sorted(out,key=lambda r:(r['bbox'][1],r['bbox'][0])),dec

_et_cw8_apply_original=et_cw8_apply
def et_cw9_apply(image,base):
    regs,visuals,cw=_et_cw8_apply_original(image,base)
    regs,dec=et_cw9_merge_unfinished_sentence(image,regs,visuals)
    cw['unfinished_sentence_decisions']=dec
    cw['rules']=cw.get('rules',[])+['UNFINISHED_SENTENCE_CANNOT_STOP_ON_SMALL_WHITESPACE']
    return regs,visuals,cw
et_cw_apply=et_cw9_apply


# ==================================================================================================
# ET-PRE-CW-PHYSICAL-SEGMENTATION-PRESERVATION-V1
#
# Generic regression protection:
#
# A cumulative reconstruction must not fragment an already coherent PRE physical
# region into multiple physical children unless the reconstruction also provides
# a structural reason to replace that geometry.
#
# This rule contains:
#   - no page reference
#   - no fixed bbox
#   - no P06-specific coordinates
#
# ==================================================================================================

_et_precw_parent_runner = examtrust_run_page


def et_precw_bbox(obj):
    if not isinstance(obj,dict):
        return None
    b=obj.get('bbox')
    if b is None:b=obj.get('full_bbox')
    if b is None:b=obj.get('core_bbox')
    if b is None:return None
    return [int(round(float(x))) for x in b]


def et_precw_area(b):
    if not b:return 0
    return max(0,b[2]-b[0])*max(0,b[3]-b[1])


def et_precw_inter(a,b):
    if not a or not b:return 0
    return (
        max(0,min(a[2],b[2])-max(a[0],b[0]))
        *
        max(0,min(a[3],b[3])-max(a[1],b[1]))
    )


def et_precw_fragmentation_evidence(pre_regs,new_regs):

    pre_boxes=[
        et_precw_bbox(r)
        for r in pre_regs
        if et_precw_bbox(r)
    ]

    new_boxes=[
        et_precw_bbox(r)
        for r in new_regs
        if et_precw_bbox(r)
    ]

    fragmented=[]

    for pi,p in enumerate(pre_boxes):

        # Ignore very small PRE physical objects.
        if et_precw_area(p)<=0:
            continue

        children=[]

        for ni,n in enumerate(new_boxes):

            inter=et_precw_inter(p,n)

            # New region substantially lies inside old physical region.
            inside_new=(
                inter /
                max(1,et_precw_area(n))
            )

            if inside_new >= .90:
                children.append({
                    'new_index':ni,
                    'bbox':n,
                    'inside_pre_ratio':inside_new
                })

        if len(children)<2:
            continue

        # Combined vertical span of children.
        union=[
            min(x['bbox'][0] for x in children),
            min(x['bbox'][1] for x in children),
            max(x['bbox'][2] for x in children),
            max(x['bbox'][3] for x in children)
        ]

        coverage=(
            et_precw_inter(p,union) /
            max(1,et_precw_area(p))
        )

        fragmented.append({
            'pre_index':pi,
            'pre_bbox':p,
            'children':children,
            'child_count':len(children),
            'union_coverage':coverage
        })

    return fragmented


def et_precw_preservation_decision(
    pre_regs,
    pre_visuals,
    new_regs,
    new_visuals
):

    fragments=et_precw_fragmentation_evidence(
        pre_regs,
        new_regs
    )

    same_visual_cardinality=(
        len(pre_visuals)==len(new_visuals)
    )

    # Strong destructive fragmentation:
    # at least one established PRE physical region becomes >=2 physical children.
    destructive=[
        x for x in fragments
        if x['child_count']>=2
    ]

    preserve=(
        bool(destructive)
        and
        same_visual_cardinality
    )

    return {
        'preserve_pre_geometry':preserve,
        'same_visual_cardinality':same_visual_cardinality,
        'pre_text_count':len(pre_regs),
        'new_text_count':len(new_regs),
        'pre_visual_count':len(pre_visuals),
        'new_visual_count':len(new_visuals),
        'fragmented_pre_regions':fragments
    }


def examtrust_run_page(
    image_path,
    page_ref,
    prev_context=None,
    output_dir=None,
    save_outputs=True
):
    # ----------------------------------------------------------------------------------------------
    # Obtain exact PRE-CW physical state.
    # ----------------------------------------------------------------------------------------------

    pre=_et_parent_examtrust_run_page(
        image_path,
        page_ref,
        prev_context,
        None,
        False
    )

    pre_regs=list(
        pre.get('text_regions')
        or []
    )

    pre_visuals=list(
        pre.get('visual_boxes')
        or pre.get('visuals')
        or []
    )

    # ----------------------------------------------------------------------------------------------
    # Run full cumulative parent normally.
    # ----------------------------------------------------------------------------------------------

    cumulative=_et_precw_parent_runner(
        image_path,
        page_ref,
        prev_context,
        None,
        False
    )

    new_regs=list(
        cumulative.get('text_regions')
        or []
    )

    new_visuals=list(
        cumulative.get('visual_boxes')
        or cumulative.get('visuals')
        or []
    )

    decision=et_precw_preservation_decision(
        pre_regs,
        pre_visuals,
        new_regs,
        new_visuals
    )

    # ----------------------------------------------------------------------------------------------
    # Preserve exact PRE physical geometry only on detected destructive fragmentation.
    # ----------------------------------------------------------------------------------------------

    if decision['preserve_pre_geometry']:

        regs=pre_regs
        visuals=pre_visuals
        action='PRESERVE_PRE_CW_PHYSICAL_GEOMETRY'

    else:

        regs=new_regs
        visuals=new_visuals
        action='KEEP_CUMULATIVE_GEOMETRY'

    image=cv2.imread(
        str(image_path),
        cv2.IMREAD_COLOR
    )

    if image is None:
        raise FileNotFoundError(str(image_path))

    H,W=image.shape[:2]

    # Reapply semantic classification to whichever physical state survives.
    regs,title_dec=files3_apply_text_title_labels(
        regs,W,H
    )

    regs,frag_dec=files3_apply_fragment_labels(
        regs,W,H
    )

    labels=build_labels(
        page_ref,
        regs,
        visuals,
        image,
        prev_context
    )

    rendered=render_page(
        image,
        regs,
        visuals,
        labels
    )

    review=rendered.copy()

    cumulative['text_regions']=regs
    cumulative['visual_boxes']=visuals
    cumulative['labels']=labels

    cumulative['pre_cw_physical_preservation']={
        'rule':'ET-PRE-CW-PHYSICAL-SEGMENTATION-PRESERVATION-V1',
        'action':action,
        'evidence':decision
    }

    cumulative['text_title_decisions_cumulative']=title_dec
    cumulative['fragment_decisions_cumulative']=frag_dec

    paths={}

    if save_outputs:

        if output_dir is None:
            raise ValueError(
                'output_dir required when save_outputs=True'
            )

        od=Path(output_dir)

        od.mkdir(
            parents=True,
            exist_ok=True
        )

        mp=od/f'{page_ref}_MANIFEST.json'
        rp=od/f'{page_ref}_RENDER.png'
        vp=od/f'{page_ref}_REVIEW.png'

        tmp=dict(cumulative)
        tmp['output_paths']={}

        mp.write_text(
            json.dumps(
                tmp,
                ensure_ascii=False,
                indent=2,
                default=str
            ),
            encoding='utf-8'
        )

        if not cv2.imwrite(str(rp),rendered):
            raise RuntimeError(str(rp))

        if not cv2.imwrite(str(vp),review):
            raise RuntimeError(str(vp))

        paths={
            'manifest':str(mp),
            'render':str(rp),
            'review':str(vp)
        }

    cumulative['output_paths']=paths

    return cumulative



# ==================================================================================================
# ET-CUMULATIVE-DESTRUCTIVE-COLLAPSE-GUARD-V1
#
# Added after ET-PRE-CW-PHYSICAL-SEGMENTATION-PRESERVATION-V1.
#
# Purpose:
# Protect an already-valid PRE physical segmentation when cumulative reconstruction
# performs a destructive many-to-one collapse without changing visual cardinality.
#
# Generic trigger only.
# No page id.
# No fixed coordinates.
#
# Cleanup:
# ET-GENERIC-PHYSICAL-TEXT-CLEANUP-V1
# ==================================================================================================

_et_p061112_parent_runner = examtrust_run_page


def et_dcg_bbox(obj):

    if not isinstance(obj,dict):
        return None

    for key in ('bbox','full_bbox','core_bbox'):

        b=obj.get(key)

        if b is not None:

            return [
                int(round(float(v)))
                for v in b
            ]

    return None


def et_dcg_area(b):

    if not b:
        return 0

    return (
        max(0,b[2]-b[0])
        *
        max(0,b[3]-b[1])
    )


def et_dcg_inter(a,b):

    if not a or not b:
        return 0

    return (
        max(
            0,
            min(a[2],b[2])
            -
            max(a[0],b[0])
        )
        *
        max(
            0,
            min(a[3],b[3])
            -
            max(a[1],b[1])
        )
    )


def et_dcg_containment(inner,outer):

    return (
        et_dcg_inter(inner,outer)
        /
        max(
            1,
            et_dcg_area(inner)
        )
    )


def et_dcg_analyze(
    image,
    pre_regs,
    pre_visuals,
    new_regs,
    new_visuals
):

    H,W=image.shape[:2]

    pre_boxes=[
        et_dcg_bbox(x)
        for x in pre_regs
        if et_dcg_bbox(x)
    ]

    new_boxes=[
        et_dcg_bbox(x)
        for x in new_regs
        if et_dcg_bbox(x)
    ]

    swallowed=[]

    max_swallowed=0

    multi_swallow_regions=0


    for ni,N in enumerate(new_boxes):

        children=[]

        for pi,P in enumerate(pre_boxes):

            ratio=et_dcg_containment(
                P,
                N
            )

            if ratio >= .90:

                children.append(
                    pi
                )


        if len(children)>=2:

            multi_swallow_regions += 1


        max_swallowed=max(
            max_swallowed,
            len(children)
        )


        swallowed.append({
            'new_index':ni,
            'new_bbox':N,
            'pre_indices':children,
            'count':len(children)
        })


    page_area=max(
        1,
        W*H
    )


    area_ratios=[
        (
            et_dcg_area(b)
            /
            page_area
        )
        for b in new_boxes
    ]


    max_new_area_ratio=max(
        area_ratios,
        default=0.0
    )


    collapse_ratio=(
        len(new_regs)
        /
        max(
            1,
            len(pre_regs)
        )
    )


    same_visual_cardinality=(
        len(pre_visuals)
        ==
        len(new_visuals)
    )


    # ----------------------------------------------------------------------------------------------
    # Generic destructive-collapse signature.
    #
    # Important:
    # This is intentionally narrower than the rejected MANY->1 rule.
    #
    # It requires simultaneously:
    #   1) visual identity count is unchanged
    #   2) strong text-count collapse
    #   3) >=3 established PRE regions swallowed by one reconstructed region
    #   4) exactly one multi-swallow reconstructed region
    #   5) reconstructed text envelope occupies a large part of the page
    #
    # P12 is excluded structurally because visual cardinality changes 4 -> 2.
    # P06 is already handled by the parent preservation layer and does not collapse.
    # ----------------------------------------------------------------------------------------------

    destructive_collapse=(
        same_visual_cardinality
        and
        len(pre_regs) >= 5
        and
        collapse_ratio < .45
        and
        max_swallowed >= 3
        and
        multi_swallow_regions == 1
        and
        max_new_area_ratio >= .28
    )


    return {

        'destructive_collapse':
            destructive_collapse,

        'pre_text_count':
            len(pre_regs),

        'new_text_count':
            len(new_regs),

        'collapse_ratio':
            collapse_ratio,

        'pre_visual_count':
            len(pre_visuals),

        'new_visual_count':
            len(new_visuals),

        'same_visual_cardinality':
            same_visual_cardinality,

        'max_swallowed':
            max_swallowed,

        'multi_swallow_regions':
            multi_swallow_regions,

        'max_new_text_page_area_ratio':
            max_new_area_ratio,

        'swallowed':
            swallowed,
    }


def et_generic_text_cleanup_v1(
    image,
    regs
):

    H,W=image.shape[:2]

    kept=[]
    removed=[]


    for r in regs:

        b=et_dcg_bbox(r)

        if not b:

            kept.append(r)
            continue


        x1,y1,x2,y2=b

        x1=max(0,min(W,x1))
        x2=max(0,min(W,x2))
        y1=max(0,min(H,y1))
        y2=max(0,min(H,y2))


        if x2<=x1 or y2<=y1:

            kept.append(r)
            continue


        crop=image[
            y1:y2,
            x1:x2
        ]


        if crop.size==0:

            kept.append(r)
            continue


        gray=cv2.cvtColor(
            crop,
            cv2.COLOR_BGR2GRAY
        )


        dark_ratio=float(
            (gray < 200).mean()
        )


        edges=cv2.Canny(
            gray,
            50,
            150
        )


        edge_ratio=float(
            (edges > 0).mean()
        )


        wr=(
            (x2-x1)
            /
            max(1,W)
        )

        hr=(
            (y2-y1)
            /
            max(1,H)
        )

        bottom=(
            y2
            /
            max(1,H)
        )

        cx=(
            ((x1+x2)/2.0)
            /
            max(1,W)
        )


        empty_artifact=(
            hr <= .015
            and
            dark_ratio <= .002
            and
            edge_ratio <= .002
        )


        footer=(
            bottom >= .93
            and
            wr <= .11
            and
            hr <= .03
            and
            (
                cx <= .15
                or
                cx >= .85
            )
            and
            dark_ratio <= .05
            and
            edge_ratio <= .07
        )


        if empty_artifact:

            removed.append({
                'bbox':b,
                'reason':'EMPTY_TEXT_ARTIFACT',
                'rule':'ET-GENERIC-PHYSICAL-TEXT-CLEANUP-V1',
                'dark_ratio':dark_ratio,
                'edge_ratio':edge_ratio
            })

            continue


        if footer:

            removed.append({
                'bbox':b,
                'reason':'PAGE_NUMBER_FOOTER',
                'rule':'ET-GENERIC-PHYSICAL-TEXT-CLEANUP-V1',
                'dark_ratio':dark_ratio,
                'edge_ratio':edge_ratio
            })

            continue


        kept.append(r)


    return (
        kept,
        removed
    )


def examtrust_run_page(
    image_path,
    page_ref,
    prev_context=None,
    output_dir=None,
    save_outputs=True
):

    image=cv2.imread(
        str(image_path),
        cv2.IMREAD_COLOR
    )

    if image is None:

        raise FileNotFoundError(
            str(image_path)
        )


    # ----------------------------------------------------------------------------------------------
    # Exact PRE-CW state.
    # ----------------------------------------------------------------------------------------------

    pre=_et_parent_examtrust_run_page(
        image_path,
        page_ref,
        prev_context,
        None,
        False
    )


    pre_regs=list(
        pre.get('text_regions')
        or []
    )


    pre_visuals=list(
        pre.get('visual_boxes')
        or
        pre.get('visuals')
        or []
    )


    # ----------------------------------------------------------------------------------------------
    # Run the FULL parent 476034 normally.
    #
    # This already includes P06 physical-preservation behavior.
    # ----------------------------------------------------------------------------------------------

    cumulative=_et_p061112_parent_runner(
        image_path,
        page_ref,
        prev_context,
        None,
        False
    )


    parent_regs=list(
        cumulative.get('text_regions')
        or []
    )


    parent_visuals=list(
        cumulative.get('visual_boxes')
        or
        cumulative.get('visuals')
        or []
    )


    analysis=et_dcg_analyze(
        image,
        pre_regs,
        pre_visuals,
        parent_regs,
        parent_visuals
    )


    # ----------------------------------------------------------------------------------------------
    # If destructive collapse is detected:
    # restore PRE physical segmentation.
    #
    # Otherwise preserve EXACT full-parent result.
    # ----------------------------------------------------------------------------------------------

    if analysis[
        'destructive_collapse'
    ]:

        regs=list(
            pre_regs
        )

        visuals=list(
            pre_visuals
        )

        action=(
            'PRESERVE_PRE_CW_AFTER_DESTRUCTIVE_COLLAPSE'
        )

    else:

        regs=list(
            parent_regs
        )

        visuals=list(
            parent_visuals
        )

        action=(
            'KEEP_FULL_PARENT_GEOMETRY'
        )


    # ----------------------------------------------------------------------------------------------
    # Generic cleanup only on the PRE-recovery path.
    #
    # This avoids changing pages for which the full parent was retained.
    # ----------------------------------------------------------------------------------------------

    removed=[]


    if analysis[
        'destructive_collapse'
    ]:

        regs,removed=et_generic_text_cleanup_v1(
            image,
            regs
        )


    # ----------------------------------------------------------------------------------------------
    # Reapply semantic classifiers after final physical geometry.
    # ----------------------------------------------------------------------------------------------

    H,W=image.shape[:2]


    regs,title_dec=files3_apply_text_title_labels(
        regs,
        W,
        H
    )


    regs,frag_dec=files3_apply_fragment_labels(
        regs,
        W,
        H
    )


    labels=build_labels(
        page_ref,
        regs,
        visuals,
        image,
        prev_context
    )


    rendered=render_page(
        image,
        regs,
        visuals,
        labels
    )


    review=rendered.copy()


    cumulative['text_regions']=regs

    cumulative['visual_boxes']=visuals

    cumulative['labels']=labels


    cumulative[
        'destructive_collapse_guard'
    ]={

        'rule':
            'ET-CUMULATIVE-DESTRUCTIVE-COLLAPSE-GUARD-V1',

        'action':
            action,

        'evidence':
            analysis,

        'removed':
            removed,
    }


    cumulative[
        'text_title_decisions_cumulative'
    ]=title_dec


    cumulative[
        'fragment_decisions_cumulative'
    ]=frag_dec


    paths={}


    if save_outputs:

        if output_dir is None:

            raise ValueError(
                'output_dir required when save_outputs=True'
            )


        od=Path(
            output_dir
        )


        od.mkdir(
            parents=True,
            exist_ok=True
        )


        mp=od/f'{page_ref}_MANIFEST.json'

        rp=od/f'{page_ref}_RENDER.png'

        vp=od/f'{page_ref}_REVIEW.png'


        temp=dict(
            cumulative
        )


        temp[
            'output_paths'
        ]={}


        mp.write_text(
            json.dumps(
                temp,
                ensure_ascii=False,
                indent=2,
                default=str
            ),
            encoding='utf-8'
        )


        if not cv2.imwrite(
            str(rp),
            rendered
        ):

            raise RuntimeError(
                str(rp)
            )


        if not cv2.imwrite(
            str(vp),
            review
        ):

            raise RuntimeError(
                str(vp)
            )


        paths={

            'manifest':
                str(mp),

            'render':
                str(rp),

            'review':
                str(vp),
        }


    cumulative[
        'output_paths'
    ]=paths


    return cumulative



# ===== ET P29 PROVEN HELPER FAMILY — PRIVATE =====

def _et29_et_step2_split_lines_by_visual_and_corridor(
    whole_lines,
    visual_boxes,
    page_width
):
    """
    STEP3 implementation.

    Physical segmentation BEFORE text grouping.

    Rules:
      A. lines physically inside confirmed Visual are removed;
      B. remaining lines are analysed in vertically-local windows;
      C. a persistent vertical whitespace corridor creates LEFT/RIGHT lanes;
      D. confirmed Visual acts as a physical obstacle:
         text cannot merge through its occupied X/Y space;
      E. full-width/crossing lines remain isolated rather than being forced
         into either lane.

    No page-specific coordinates.
    """

    # ----------------------------------------------------------------------------------------------
    # 1. Remove internal Visual text from Text candidate inventory.
    # ----------------------------------------------------------------------------------------------

    text_lines = []

    for ln in whole_lines:

        lb = ln["bbox"]

        inside_visual = False

        for vb in visual_boxes:

            if _et29_et_step2_line_inside_ratio(
                lb,
                vb
            ) >= 0.70:

                inside_visual = True
                break

        if not inside_visual:
            text_lines.append(
                dict(ln)
            )

    if len(text_lines) < 4:
        return text_lines, []

    text_lines.sort(
        key=lambda z: (
            float(z["bbox"][1]),
            float(z["bbox"][0])
        )
    )

    heights = [
        max(
            1.0,
            float(x["bbox"][3])
            - float(x["bbox"][1])
        )
        for x in text_lines
    ]

    med_h = (
        statistics.median(heights)
        if heights
        else 7.0
    )

    # ----------------------------------------------------------------------------------------------
    # 2. Build local Y windows.
    #
    # Important:
    # We do NOT require a blank horizontal band.
    # Two-column layouts naturally interleave left/right lines in Y.
    #
    # A window continues while vertical distance remains locally connected.
    # ----------------------------------------------------------------------------------------------

    windows = []

    current = []
    current_bottom = None

    for ln in text_lines:

        b = ln["bbox"]

        y1 = float(b[1])
        y2 = float(b[3])

        if not current:

            current = [ln]
            current_bottom = y2
            continue

        gap = y1 - float(current_bottom)

        # Larger than Step2's strict split.
        # This permits left/right column lines to coexist in same window.
        if gap > med_h * 4.5:

            windows.append(current)

            current = [ln]
            current_bottom = y2

        else:

            current.append(ln)
            current_bottom = max(
                float(current_bottom),
                y2
            )

    if current:
        windows.append(current)

    output = []
    decisions = []

    # ----------------------------------------------------------------------------------------------
    # 3. Split each connected window by persistent whitespace.
    # ----------------------------------------------------------------------------------------------

    for wi, window in enumerate(windows):

        corridor = _et29_et_step2_vertical_corridor(
            window,
            float(page_width)
        )

        if corridor is None:

            for ln in window:
                ln = dict(ln)
                ln["_et_lane"] = (
                    ln.get("_et_lane")
                    or f"W{wi}_MAIN"
                )
                output.append(ln)

            continue

        # Determine actual whitespace margin around corridor.
        #
        # We do not need exact run boundaries here; use a narrow safety
        # moat around detected center so glyphs close to corridor are not
        # assigned across it.
        safety = max(
            2.0,
            float(page_width) * 0.008
        )

        left = []
        right = []
        crossing = []

        for ln in window:

            b = ln["bbox"]

            x1 = float(b[0])
            x2 = float(b[2])

            if x2 <= corridor - safety:

                left.append(ln)

            elif x1 >= corridor + safety:

                right.append(ln)

            else:

                crossing.append(ln)

        crossing_ratio = (
            len(crossing)
            / max(1, len(window))
        )

        accepted = (
            len(left) >= 2
            and len(right) >= 2
            and crossing_ratio <= 0.18
        )

        decisions.append({
            "window": int(wi),
            "corridor_x": round(
                float(corridor),
                2
            ),
            "left_lines": len(left),
            "right_lines": len(right),
            "crossing_lines": len(crossing),
            "crossing_ratio": round(
                float(crossing_ratio),
                3
            ),
            "accepted": bool(accepted),
        })

        if not accepted:

            for ln in window:

                ln = dict(ln)

                ln["_et_lane"] = (
                    ln.get("_et_lane")
                    or f"W{wi}_MAIN"
                )

                output.append(ln)

            continue

        for ln in left:

            ln = dict(ln)
            ln["_et_lane"] = f"W{wi}_LEFT"
            output.append(ln)

        for ln in right:

            ln = dict(ln)
            ln["_et_lane"] = f"W{wi}_RIGHT"
            output.append(ln)

        # Crossing line cannot bridge LEFT and RIGHT.
        for ci, ln in enumerate(crossing):

            ln = dict(ln)

            ln["_et_lane"] = (
                f"W{wi}_CROSS_{ci}"
            )

            output.append(ln)

    # ----------------------------------------------------------------------------------------------
    # 4. Visual obstacle pass.
    #
    # If a text line overlaps the vertical range of a confirmed Visual,
    # mark whether it physically belongs LEFT or RIGHT of that Visual.
    #
    # This is stronger than punctuation or normal paragraph continuation.
    # ----------------------------------------------------------------------------------------------

    final = []

    for ln in output:

        ln = dict(ln)

        b = ln["bbox"]

        lx1 = float(b[0])
        ly1 = float(b[1])
        lx2 = float(b[2])
        ly2 = float(b[3])

        for vi, vb in enumerate(
            visual_boxes
        ):

            vx1, vy1, vx2, vy2 = [
                float(z)
                for z in vb
            ]

            y_overlap = (
                min(ly2, vy2)
                - max(ly1, vy1)
            )

            if y_overlap <= 0:
                continue

            # Real whitespace is required between line and Visual.
            gap_left = vx1 - lx2
            gap_right = lx1 - vx2

            if gap_left > 0:

                ln["_et_visual_lane"] = (
                    f"V{vi}_LEFT"
                )

            elif gap_right > 0:

                ln["_et_visual_lane"] = (
                    f"V{vi}_RIGHT"
                )

            else:

                # It intersects Visual geometry.
                # It must never bridge around it.
                ln["_et_visual_lane"] = (
                    f"V{vi}_INTERSECT"
                )

        final.append(ln)

    final.sort(
        key=lambda z: (
            float(z["bbox"][1]),
            float(z["bbox"][0])
        )
    )

    return final, decisions

def _et29_et_step2_filter_text_dominant_visuals(
    visuals,
    whole_lines
):
    """
    Filter only already-created visual objects.

    Returns:
      kept_visuals,
      decisions
    """

    kept = []
    decisions = []

    for v in visuals:

        b = (
            v.get("full_bbox")
            or v.get("core_bbox")
            or v.get("bbox")
        )

        if b is None:
            kept.append(v)
            continue

        reject, evidence = _et29_et_step2_visual_text_dominant(
            b,
            whole_lines
        )

        decisions.append({
            "bbox": [int(round(float(z))) for z in b],
            "reject": bool(reject),
            "evidence": evidence,
        })

        if not reject:
            kept.append(v)

    return kept, decisions

def _et29_et_step2_parent_extract_whole_lines(page_bgr, exclusions):
    ph, pw = page_bgr.shape[:2]
    gray = cv2.cvtColor(page_bgr, cv2.COLOR_BGR2GRAY)
    mask = np.ones((ph, pw), dtype=np.uint8) * 255

    for box in exclusions:
        x1, y1, x2, y2 = [int(v) for v in box]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(pw, x2), min(ph, y2)
        if x2 > x1 and y2 > y1:
            mask[y1:y2, x1:x2] = 0

    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 15
    )
    binary[mask == 0] = 0

    count, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)

    comps = []
    for i in range(1, count):
        x = int(stats[i, cv2.CC_STAT_LEFT])
        y = int(stats[i, cv2.CC_STAT_TOP])
        cw = int(stats[i, cv2.CC_STAT_WIDTH])
        ch = int(stats[i, cv2.CC_STAT_HEIGHT])
        ca = int(stats[i, cv2.CC_STAT_AREA])
        if 2 <= ch <= ph * 0.055 and 1 <= cw <= pw * 0.10 and ca >= 2:
            comps.append({"bbox": [x, y, x + cw, y + ch],
                          "cx": float(centroids[i][0]), "cy": float(centroids[i][1])})

    if len(comps) < 10:
        return {"whole_lines": [], "glyph_h_med": 1.0}

    heights = [c["bbox"][3] - c["bbox"][1] for c in comps]
    glyph_h_med = float(np.median(heights))
    baseline_tol = max(2.0, glyph_h_med * 0.70)

    rows = []
    for comp in sorted(comps, key=lambda c: (c["cy"], c["cx"])):
        best_idx, best_dist = None, None
        for idx, row in enumerate(rows):
            d = abs(comp["cy"] - row["center_y"])
            if d <= baseline_tol and (best_dist is None or d < best_dist):
                best_idx, best_dist = idx, d
        if best_idx is None:
            rows.append({"components": [comp], "center_y": comp["cy"]})
        else:
            rows[best_idx]["components"].append(comp)
            rows[best_idx]["center_y"] = float(
                np.median([c["cy"] for c in rows[best_idx]["components"]])
            )

    whole_lines = []
    for row in rows:
        row_comps = sorted(row["components"], key=lambda c: c["bbox"][0])
        if len(row_comps) < 2:
            continue

        gaps = [b["bbox"][0] - a["bbox"][2] for a, b in zip(row_comps[:-1], row_comps[1:])]
        positive_gaps = [g for g in gaps if g >= 0]
        normal_gap = float(np.median(positive_gaps)) if positive_gaps else 0.0

        groups = [[row_comps[0]]]
        for prev, cur in zip(row_comps[:-1], row_comps[1:]):
            gap = cur["bbox"][0] - prev["bbox"][2]
            split_gap = gap > normal_gap + glyph_h_med * 3.0
            if split_gap:
                groups.append([cur])
            else:
                groups[-1].append(cur)

        for group in groups:
            if len(group) < 2:
                continue
            box = union_box([c["bbox"] for c in group])
            if any(boxes_intersect(box, ex) > 0 for ex in exclusions):
                continue
            x1, y1, x2, y2 = box
            whole_lines.append({
                "bbox": [x1, y1, x2, y2],
                "left": x1, "right": x2, "width": x2 - x1, "height": y2 - y1,
                "component_count": len(group),
                "baseline_y": float(row["center_y"]),
            })

    whole_lines.sort(key=lambda r: (r["bbox"][1], r["bbox"][0]))
    return {"whole_lines": whole_lines, "glyph_h_med": glyph_h_med}

def _et29_et_step2_visual_text_dominant(vbox, whole_lines):
    """
    Reject candidates that behave like decorative text containers rather
    than a real figure/graph.

    This does NOT use OCR words and does NOT use page coordinates.

    Evidence:
      - candidate is broad
      - relatively shallow
      - only a modest number of complete text lines
      - lines form a predominantly text-like block
      - no dense internal graphical fragmentation evidence

    The narrow mixed-visual protection from Step 1B remains authoritative
    for compact graph/figure candidates.
    """

    x1, y1, x2, y2 = [float(z) for z in vbox]

    w = max(1.0, x2 - x1)
    h = max(1.0, y2 - y1)

    aspect = w / h

    inside = []

    for ln in whole_lines:
        lb = ln["bbox"]

        if _et29_et_step2_line_inside_ratio(lb, vbox) >= 0.70:
            inside.append(ln)

    if not inside:
        return False, {
            "inside_lines": 0,
            "reason": "NO_TEXT_EVIDENCE"
        }

    lefts = [
        float(x["bbox"][0])
        for x in inside
    ]

    widths = [
        max(
            1.0,
            float(x["bbox"][2]) - float(x["bbox"][0])
        )
        for x in inside
    ]

    left_std = (
        statistics.pstdev(lefts) / w
        if len(lefts) > 1
        else 0.0
    )

    width_std = (
        statistics.pstdev(widths) / w
        if len(widths) > 1
        else 0.0
    )

    overlap = text_overlap_ratio(
        vbox,
        whole_lines
    )

    # Broad/shallow callout/container shape.
    broad_container = (
        aspect >= 1.75
    )

    # Text container typically has a limited set of real complete lines.
    modest_line_count = (
        3 <= len(inside) <= 12
    )

    # Enough textual evidence to be suspicious.
    meaningful_text = (
        overlap >= 0.24
    )

    # Do not reject compact square-ish figures here.
    reject = (
        broad_container
        and modest_line_count
        and meaningful_text
    )

    return reject, {
        "inside_lines": int(len(inside)),
        "aspect": round(float(aspect), 3),
        "text_overlap": round(float(overlap), 3),
        "left_std_ratio": round(float(left_std), 3),
        "width_std_ratio": round(float(width_std), 3),
        "broad_container": bool(broad_container),
        "modest_line_count": bool(modest_line_count),
        "meaningful_text": bool(meaningful_text),
        "decision": (
            "REJECT_TEXT_DOMINANT_CONTAINER"
            if reject
            else
            "KEEP_VISUAL"
        ),
    }

def _et29_paragraph_geometry_signal(box, whole_lines):
    """
    Conservative paragraph pre-filter with narrow mixed-visual rescue.

    DEFAULT:
        Preserve the accepted broad paragraph rejection behaviour.

    EXCEPTION:
        A candidate may escape paragraph rejection only when there is
        strong geometric evidence of a compact mixed visual containing
        spatially dispersed internal labels.

    Returning False only allows the existing visual validator to inspect
    the candidate. It does not itself classify the candidate as Visual.

    Generic only. No page-specific coordinates.
    """

    bx1, by1, bx2, by2 = [float(v) for v in box]

    bw = max(1.0, bx2 - bx1)
    bh = max(1.0, by2 - by1)

    inside = []

    for ln in whole_lines:

        lb = ln["bbox"]

        inter = boxes_intersect(
            box,
            lb
        )

        la = bbox_area(lb)

        if la > 0 and inter / la >= 0.70:
            inside.append(ln)

    overlap = text_overlap_ratio(
        box,
        whole_lines
    )

    lefts = [
        float(ln["bbox"][0])
        for ln in inside
    ]

    rights = [
        float(ln["bbox"][2])
        for ln in inside
    ]

    widths = [
        max(
            1.0,
            float(ln["bbox"][2] - ln["bbox"][0])
        )
        for ln in inside
    ]

    centers = [
        (
            float(ln["bbox"][0])
            + float(ln["bbox"][2])
        ) / 2.0
        for ln in inside
    ]

    left_std_ratio = (
        statistics.pstdev(lefts) / bw
        if len(lefts) > 1
        else 0.0
    )

    right_std_ratio = (
        statistics.pstdev(rights) / bw
        if len(rights) > 1
        else 0.0
    )

    width_std_ratio = (
        statistics.pstdev(widths) / bw
        if len(widths) > 1
        else 0.0
    )

    center_std_ratio = (
        statistics.pstdev(centers) / bw
        if len(centers) > 1
        else 0.0
    )

    aspect_wh = bw / bh

    # ----------------------------------------------------------------------------------------------
    # ACCEPTED EXISTING P06 PROTECTION — PRESERVE
    # ----------------------------------------------------------------------------------------------

    p06_mixed_visual_protect = (
        3 <= len(inside) <= 12
        and overlap >= 0.55
        and 0.15 <= left_std_ratio < 0.20
        and 0.90 <= aspect_wh <= 1.45
    )

    # ----------------------------------------------------------------------------------------------
    # NEW GENERIC NARROW RESCUE
    #
    # Strongly dispersed internal labels in a compact candidate.
    #
    # P29 graph evidence:
    #   aspect ≈ 1.108
    #   left/right/width/center dispersion is heterogeneous
    #   19 internal whole-line fragments
    #
    # This deliberately DOES NOT rescue:
    #   - broad horizontal text blocks
    #   - tall text columns
    #   - ordinary callout paragraphs
    #
    # No coordinates / page ID are used.
    # ----------------------------------------------------------------------------------------------

    dispersion_votes = sum([
        left_std_ratio   >= 0.15,
        right_std_ratio  >= 0.18,
        width_std_ratio  >= 0.18,
        center_std_ratio >= 0.16,
    ])

    compact_figure_geometry = (
        0.80 <= aspect_wh <= 1.60
    )

    enough_internal_structure = (
        len(inside) >= 8
    )

    heterogeneous_labels = (
        dispersion_votes >= 3
    )

    not_clean_paragraph_column = (
        left_std_ratio >= 0.15
    )

    mixed_layout_visual_protect = (
        compact_figure_geometry
        and enough_internal_structure
        and heterogeneous_labels
        and not_clean_paragraph_column
    )

    visual_protect = (
        p06_mixed_visual_protect
        or mixed_layout_visual_protect
    )

    # ----------------------------------------------------------------------------------------------
    # ORIGINAL ACCEPTED PARAGRAPH BEHAVIOUR RESTORED AS DEFAULT
    #
    # Do NOT replace this with "paragraph_layout required".
    # Step01 proved that doing so opens the visual gate too widely.
    # ----------------------------------------------------------------------------------------------

    original_paragraph_signal = (
        (
            left_std_ratio < 0.15
            and overlap >= 0.25
        )
        or
        (
            overlap >= 0.30
        )
    )

    is_paragraph = (
        original_paragraph_signal
        and not visual_protect
    )

    return is_paragraph, {
        "lines_inside":
            int(len(inside)),

        "left_std_ratio":
            round(float(left_std_ratio), 3),

        "right_std_ratio":
            round(float(right_std_ratio), 3),

        "width_std_ratio":
            round(float(width_std_ratio), 3),

        "center_std_ratio":
            round(float(center_std_ratio), 3),

        "text_overlap":
            round(float(overlap), 3),

        "aspect_wh":
            round(float(aspect_wh), 3),

        "dispersion_votes":
            int(dispersion_votes),

        "compact_figure_geometry":
            bool(compact_figure_geometry),

        "enough_internal_structure":
            bool(enough_internal_structure),

        "heterogeneous_labels":
            bool(heterogeneous_labels),

        "p06_mixed_visual_protect":
            bool(p06_mixed_visual_protect),

        "mixed_layout_visual_protect":
            bool(mixed_layout_visual_protect),

        "visual_protect":
            bool(visual_protect),

        "original_paragraph_signal":
            bool(original_paragraph_signal),

        "decision":
            (
                "PARAGRAPH_REJECT"
                if is_paragraph
                else
                "ALLOW_EXISTING_VISUAL_VALIDATOR"
            ),
    }

def _et29_et_step2_line_inside_ratio(line_box, box):
    inter = _et29_et_step2_box_intersection(line_box, box)

    la = max(
        1.0,
        (float(line_box[2]) - float(line_box[0]))
        * (float(line_box[3]) - float(line_box[1]))
    )

    return inter / la

def _et29_et_step2_vertical_corridor(
    lines,
    page_width,
    min_gap_ratio=0.045,
    min_side_lines=2
):
    """
    STEP3 implementation.

    Detect a REAL persistent vertical whitespace corridor.

    Unlike Step2, this does not search pairwise line gaps.

    Method:
      1. project all text-line horizontal occupancy onto X;
      2. find X intervals crossed by very few text lines;
      3. require substantial text population on BOTH sides;
      4. prefer an interior corridor with strong persistence.

    Returns corridor midpoint or None.

    Generic geometry only.
    """

    if len(lines) < 4:
        return None

    W = max(
        1,
        int(round(float(page_width)))
    )

    occupancy = np.zeros(
        W,
        dtype=np.int32
    )

    valid = []

    for ln in lines:

        b = ln["bbox"]

        x1 = max(
            0,
            min(
                W - 1,
                int(np.floor(float(b[0])))
            )
        )

        x2 = max(
            x1 + 1,
            min(
                W,
                int(np.ceil(float(b[2])))
            )
        )

        occupancy[x1:x2] += 1

        valid.append((
            float(b[0]),
            float(b[2])
        ))

    # Interior page only.
    lo = int(round(W * 0.12))
    hi = int(round(W * 0.88))

    min_gap = max(
        8,
        int(round(W * min_gap_ratio))
    )

    # A true corridor may be crossed by an occasional formula/caption,
    # but cannot be occupied by a substantial fraction of the lines.
    max_cross = max(
        1,
        int(round(len(valid) * 0.08))
    )

    whiteish = (
        occupancy <= max_cross
    )

    runs = []

    start = None

    for x in range(lo, hi):

        if whiteish[x]:

            if start is None:
                start = x

        else:

            if start is not None:

                if x - start >= min_gap:
                    runs.append(
                        (start, x)
                    )

                start = None

    if start is not None:

        if hi - start >= min_gap:
            runs.append(
                (start, hi)
            )

    candidates = []

    for x1, x2 in runs:

        mid = (
            float(x1) + float(x2)
        ) / 2.0

        left_count = sum(
            1
            for a, b in valid
            if b <= x1
        )

        right_count = sum(
            1
            for a, b in valid
            if a >= x2
        )

        crossing_count = sum(
            1
            for a, b in valid
            if a < x2 and b > x1
        )

        if (
            left_count < min_side_lines
            or right_count < min_side_lines
        ):
            continue

        crossing_ratio = (
            crossing_count
            / max(1, len(valid))
        )

        if crossing_ratio > 0.15:
            continue

        width = x2 - x1

        balance = min(
            left_count,
            right_count
        ) / max(
            left_count,
            right_count
        )

        # Prefer wide + balanced + persistent corridor.
        score = (
            float(width)
            * (0.5 + balance)
            * (1.0 - crossing_ratio)
        )

        candidates.append({
            "x1": int(x1),
            "x2": int(x2),
            "mid": float(mid),
            "width": int(width),
            "left_count": int(left_count),
            "right_count": int(right_count),
            "crossing_count": int(crossing_count),
            "crossing_ratio": float(crossing_ratio),
            "score": float(score),
        })

    if not candidates:
        return None

    candidates.sort(
        key=lambda z: z["score"],
        reverse=True
    )

    return float(
        candidates[0]["mid"]
    )

def _et29_et_phys_line_inside_visual(lb, visual_boxes):
    """
    Confirmed Visual is a hard physical obstacle.
    Internal visual labels/caption must not become Text.
    """

    la = max(1, _et29_et_phys_area(lb))

    for vb in visual_boxes:

        inter = _et29_et_phys_inter(lb, vb)

        if inter / la >= 0.55:
            return True

    return False

def _et29_et_step2_box_intersection(a, b):
    x1 = max(float(a[0]), float(b[0]))
    y1 = max(float(a[1]), float(b[1]))
    x2 = min(float(a[2]), float(b[2]))
    y2 = min(float(a[3]), float(b[3]))

    if x2 <= x1 or y2 <= y1:
        return 0.0

    return (x2 - x1) * (y2 - y1)

def _et29_et_phys_union_line_boxes(lines):
    boxes = [x["bbox"] for x in lines]

    return [
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    ]

def _et29_et_phys_resolve_regions(image, regions, visuals):
    """
    Generic final physical resolver.

    No page-specific coordinates.
    """

    H, W = image.shape[:2]

    visual_boxes = [
        _et29_et_phys_bbox(v)
        for v in visuals
        if _et29_et_phys_bbox(v)
    ]

    # IMPORTANT:
    # obtain RAW lines without visual exclusion first.
    # Visual-internal lines are removed explicitly by physical membership.
    lr = extract_whole_lines(
        image,
        exclusions=[]
    )

    whole_lines = [
        dict(x)
        for x in lr.get("whole_lines", [])
    ]

    glyph = float(
        lr.get("glyph_h_med", 7) or 7
    )

    resolved = []
    decisions = []

    for r0 in regions:

        r = dict(r0)

        # Structural title/formula/marker records should not be arbitrarily
        # divided by a column detector.
        role = str(
            r.get("semantic_role", "")
        ).upper()

        if role in (
            "TITLE",
            "FORMULA",
            "MARKER_TEXT"
        ):
            resolved.append(r)
            continue

        # ------------------------------------------------------------------
        # First remove confirmed Visual occupancy.
        # ------------------------------------------------------------------

        r, vdec = et_phys_remove_text_visual_overlap(
            r,
            whole_lines,
            visual_boxes
        )

        if vdec:
            decisions.append(vdec)

        # ------------------------------------------------------------------
        # Then resolve internal whitespace islands.
        #
        # Two passes are enough for ordinary textbook layouts:
        # one candidate can become LEFT/RIGHT, and a child can itself reveal
        # another physical split. This is generic recursion bounded for safety.
        # ------------------------------------------------------------------

        current = [r]

        for depth in range(2):

            nxt = []
            changed = False

            for item in current:

                pieces, dec = (
                    et_phys_split_candidate_once(
                        item,
                        whole_lines,
                        visual_boxes,
                        glyph,
                        W
                    )
                )

                if dec and len(pieces) > 1:
                    changed = True
                    decisions.append(dec)

                nxt.extend(pieces)

            current = nxt

            if not changed:
                break

        resolved.extend(current)

    # ----------------------------------------------------------------------
    # Final hard validator:
    # no finalized Text physical box may overlap a confirmed Visual.
    # ----------------------------------------------------------------------

    final = []

    for r in resolved:

        rb = _et29_et_phys_bbox(r)

        overlap = any(
            _et29_et_phys_inter(rb, vb) > 0
            for vb in visual_boxes
        )

        if overlap:
            nr = dict(r)
            nr["hold"] = True
            nr.setdefault(
                "hold_reasons",
                []
            ).append(
                "PHYSICAL_TEXT_VISUAL_OVERLAP"
            )
            final.append(nr)

        else:
            final.append(r)

    final.sort(
        key=lambda r: (
            _et29_et_phys_bbox(r)[1],
            _et29_et_phys_bbox(r)[0]
        )
    )

    return final, decisions

def _et29_et_step2_same_lane(a, b):
    """
    Existing grouping functions may call this guard.
    Unmarked legacy lines remain compatible.
    """

    la = a.get("_et_lane")
    lb = b.get("_et_lane")

    if la is None or lb is None:
        return True

    return la == lb

def _et29_et_phys_inter(a, b):
    if not a or not b:
        return 0

    return (
        max(0, min(a[2], b[2]) - max(a[0], b[0]))
        *
        max(0, min(a[3], b[3]) - max(a[1], b[1]))
    )

def _et29_et_phys_bbox(obj):
    if obj is None:
        return None

    if isinstance(obj, (list, tuple)) and len(obj) == 4:
        return [int(x) for x in obj]

    for key in ("bbox", "full_bbox", "core_bbox"):
        b = obj.get(key) if isinstance(obj, dict) else None
        if b:
            return [int(x) for x in b]

    return None

def _et29_et_phys_area(b):
    if not b:
        return 0

    return max(0, b[2]-b[0]) * max(0, b[3]-b[1])


# ==================================================================================================
# ET-PHYSICAL-MIXED-LAYOUT-ACTIVATION-V1
#
# Default path: exact SAFE behavior.
#
# Specialized physical-layout branch activates only when the page contains
# a compact, internally heterogeneous visual candidate that the SAFE paragraph
# pre-filter would otherwise reject.
#
# No page ID.
# No fixed coordinates.
# ==================================================================================================

_et29_safe_paragraph_geometry_signal = _paragraph_geometry_signal
_et29_safe_run_visual_stage = run_visual_stage
_et29_safe_examtrust_run_page = examtrust_run_page


def _et29_candidate_activation_evidence(image_bgr):

    raw = raw_visual_candidates(image_bgr)

    line_result = extract_whole_lines(
        image_bgr,
        exclusions=[]
    )

    whole_lines = line_result.get(
        "whole_lines",
        []
    )

    activation = []

    for candidate in raw:

        box = (
            candidate.get("bbox")
            if isinstance(candidate, dict)
            else candidate
        )

        if box is None:
            continue

        safe_is_para, safe_ev = (
            _et29_safe_paragraph_geometry_signal(
                box,
                whole_lines
            )
        )

        oracle_is_para, oracle_ev = (
            _et29_paragraph_geometry_signal(
                box,
                whole_lines
            )
        )

        if not safe_is_para:
            continue

        if oracle_is_para:
            continue

        lines_inside = int(
            oracle_ev.get(
                "lines_inside",
                0
            )
        )

        aspect = float(
            oracle_ev.get(
                "aspect_wh",
                999.0
            )
        )

        left_std = float(
            oracle_ev.get(
                "left_std_ratio",
                999.0
            )
        )

        right_std = float(
            oracle_ev.get(
                "right_std_ratio",
                0.0
            )
        )

        width_std = float(
            oracle_ev.get(
                "width_std_ratio",
                0.0
            )
        )

        center_std = float(
            oracle_ev.get(
                "center_std_ratio",
                0.0
            )
        )

        narrow_compact_mixed_layout = (
            0.95 <= aspect <= 1.30
            and 10 <= lines_inside <= 24
            and 0.145 <= left_std <= 0.20
            and right_std >= 0.22
            and width_std >= 0.22
            and center_std >= 0.16
        )

        if narrow_compact_mixed_layout:

            activation.append({
                "bbox": list(map(int, box)),
                "safe_is_paragraph": bool(
                    safe_is_para
                ),
                "oracle_is_paragraph": bool(
                    oracle_is_para
                ),
                "lines_inside": lines_inside,
                "aspect": aspect,
                "left_std_ratio": left_std,
                "right_std_ratio": right_std,
                "width_std_ratio": width_std,
                "center_std_ratio": center_std,
                "rule":
                    "ET-PHYSICAL-MIXED-LAYOUT-ACTIVATION-V1",
            })

    return activation


def _et29_run_visual_stage_gated(
    image_bgr,
    container,
):

    activation = (
        _et29_candidate_activation_evidence(
            image_bgr
        )
    )

    if not activation:

        result = _et29_safe_run_visual_stage(
            image_bgr,
            container
        )

        if isinstance(result, dict):
            result = dict(result)
            result[
                "et29_activation"
            ] = {
                "active": False,
                "evidence": [],
            }

        return result

    # ----------------------------------------------------------------------
    # Temporarily use proven Oracle paragraph signal ONLY for this visual run.
    # SAFE global definition is restored immediately.
    # ----------------------------------------------------------------------

    global _paragraph_geometry_signal

    original_signal = _paragraph_geometry_signal

    try:

        _paragraph_geometry_signal = (
            _et29_paragraph_geometry_signal
        )

        result = (
            _et29_safe_run_visual_stage(
                image_bgr,
                container
            )
        )

    finally:

        _paragraph_geometry_signal = (
            original_signal
        )

    # ----------------------------------------------------------------------
    # Apply proven text-dominant-container rejection.
    # ----------------------------------------------------------------------

    if isinstance(result, dict):

        visuals = result.get(
            "visuals",
            []
        )

        # Exact Oracle API:
        # et_step2_filter_text_dominant_visuals(visuals, whole_lines)
        _et29_line_result = extract_whole_lines(
            image_bgr,
            exclusions=[]
        )

        _et29_whole_lines = list(
            _et29_line_result.get(
                "whole_lines",
                []
            )
        )

        filtered_result = (
            _et29_et_step2_filter_text_dominant_visuals(
                visuals,
                _et29_whole_lines,
            )
        )

        # Oracle helper may return either list or tuple(list, decisions).
        if isinstance(filtered_result, tuple):
            filtered_visuals = filtered_result[0]
            filter_decisions = (
                filtered_result[1]
                if len(filtered_result) > 1
                else []
            )
        else:
            filtered_visuals = filtered_result
            filter_decisions = []

        result = dict(result)
        result["visuals"] = filtered_visuals

        result[
            "et29_activation"
        ] = {
            "active": True,
            "evidence": activation,
            "filter_decisions":
                filter_decisions,
        }

    return result


# Replace ONLY run_visual_stage with the gate.
run_visual_stage = _et29_run_visual_stage_gated


# ==================================================================================================
# TOP-LEVEL GATED PHYSICAL RESOLUTION
#
# We allow the SAFE page pipeline to execute normally.
#
# The physical resolver is applied only when the same strong mixed-layout
# activation evidence is present.
# ==================================================================================================

def examtrust_run_page(*args, **kwargs):

    result = _et29_safe_examtrust_run_page(
        *args,
        **kwargs
    )

    # Find image/path from actual caller arguments without inventing another API.
    source = (
        args[0]
        if len(args) >= 1
        else kwargs.get("image_path")
    )

    if source is None:
        return result

    import cv2 as _et29_cv2

    if isinstance(source, (str, bytes)):
        image_bgr = _et29_cv2.imread(
            str(source),
            _et29_cv2.IMREAD_COLOR
        )
    elif hasattr(source, "__fspath__"):
        image_bgr = _et29_cv2.imread(
            str(source),
            _et29_cv2.IMREAD_COLOR
        )
    else:
        image_bgr = source

    if image_bgr is None:
        return result

    activation = (
        _et29_candidate_activation_evidence(
            image_bgr
        )
    )

    if not activation:
        return result

    # ----------------------------------------------------------------------------------------------
    # Use the proven P29 resolver only after SAFE page construction.
    # ----------------------------------------------------------------------------------------------

    text_regions = result.get(
        "text_regions",
        []
    )

    visual_boxes = result.get(
        "visual_boxes",
        []
    )

    try:

        resolved = (
            _et29_et_phys_resolve_regions(
                image_bgr,
                text_regions,
                visual_boxes,
            )
        )

    except TypeError:

        # Do not silently guess alternative API.
        # Record that activation occurred but resolver signature needs exact use.
        result = dict(result)

        result[
            "et29_physical_resolution"
        ] = {
            "active": True,
            "status":
                "RESOLVER_SIGNATURE_NOT_MATCHED",
        }

        return result

    if isinstance(resolved, tuple):

        new_regions = resolved[0]

        decisions = (
            resolved[1]
            if len(resolved) > 1
            else []
        )

    else:

        new_regions = resolved
        decisions = []

    result = dict(result)
    result["text_regions"] = new_regions

    result[
        "et29_physical_resolution"
    ] = {
        "active": True,
        "status": "APPLIED",
        "decisions": decisions,
    }

    # Rebuild labels with standard pipeline label builder.
    if "build_labels" in globals():

        try:
            result["labels"] = build_labels(
                result.get(
                    "text_regions",
                    []
                ),
                result.get(
                    "visual_boxes",
                    []
                ),
            )
        except Exception:
            # Do not alter physical geometry if label signature differs.
            pass

    return result



# ===== ET-P29 AST-SAFE PHYSICAL CLOSURE =====

def _et29d_union_box(boxes):
    xs1 = [b[0] for b in boxes]
    ys1 = [b[1] for b in boxes]
    xs2 = [b[2] for b in boxes]
    ys2 = [b[3] for b in boxes]
    return [min(xs1), min(ys1), max(xs2), max(ys2)]

def _et29d_boxes_intersect(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = (max(ax1, bx1), max(ay1, by1))
    ix2, iy2 = (min(ax2, bx2), min(ay2, by2))
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    return (ix2 - ix1) * (iy2 - iy1)

def _et29d_extract_whole_lines(page_bgr, exclusions):
    ph, pw = page_bgr.shape[:2]
    gray = cv2.cvtColor(page_bgr, cv2.COLOR_BGR2GRAY)
    mask = np.ones((ph, pw), dtype=np.uint8) * 255
    for box in exclusions:
        x1, y1, x2, y2 = [int(v) for v in box]
        x1, y1 = (max(0, x1), max(0, y1))
        x2, y2 = (min(pw, x2), min(ph, y2))
        if x2 > x1 and y2 > y1:
            mask[y1:y2, x1:x2] = 0
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 15)
    binary[mask == 0] = 0
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
    comps = []
    for i in range(1, count):
        x = int(stats[i, cv2.CC_STAT_LEFT])
        y = int(stats[i, cv2.CC_STAT_TOP])
        cw = int(stats[i, cv2.CC_STAT_WIDTH])
        ch = int(stats[i, cv2.CC_STAT_HEIGHT])
        ca = int(stats[i, cv2.CC_STAT_AREA])
        if 2 <= ch <= ph * 0.055 and 1 <= cw <= pw * 0.1 and (ca >= 2):
            comps.append({'bbox': [x, y, x + cw, y + ch], 'cx': float(centroids[i][0]), 'cy': float(centroids[i][1])})
    if len(comps) < 10:
        return {'whole_lines': [], 'glyph_h_med': 1.0}
    heights = [c['bbox'][3] - c['bbox'][1] for c in comps]
    glyph_h_med = float(np.median(heights))
    baseline_tol = max(2.0, glyph_h_med * 0.7)
    rows = []
    for comp in sorted(comps, key=lambda c: (c['cy'], c['cx'])):
        best_idx, best_dist = (None, None)
        for idx, row in enumerate(rows):
            d = abs(comp['cy'] - row['center_y'])
            if d <= baseline_tol and (best_dist is None or d < best_dist):
                best_idx, best_dist = (idx, d)
        if best_idx is None:
            rows.append({'components': [comp], 'center_y': comp['cy']})
        else:
            rows[best_idx]['components'].append(comp)
            rows[best_idx]['center_y'] = float(np.median([c['cy'] for c in rows[best_idx]['components']]))
    whole_lines = []
    for row in rows:
        row_comps = sorted(row['components'], key=lambda c: c['bbox'][0])
        if len(row_comps) < 2:
            continue
        gaps = [b['bbox'][0] - a['bbox'][2] for a, b in zip(row_comps[:-1], row_comps[1:])]
        positive_gaps = [g for g in gaps if g >= 0]
        normal_gap = float(np.median(positive_gaps)) if positive_gaps else 0.0
        groups = [[row_comps[0]]]
        for prev, cur in zip(row_comps[:-1], row_comps[1:]):
            gap = cur['bbox'][0] - prev['bbox'][2]
            split_gap = gap > normal_gap + glyph_h_med * 3.0
            if split_gap:
                groups.append([cur])
            else:
                groups[-1].append(cur)
        for group in groups:
            if len(group) < 2:
                continue
            box = _et29d_union_box([c['bbox'] for c in group])
            if any((_et29d_boxes_intersect(box, ex) > 0 for ex in exclusions)):
                continue
            x1, y1, x2, y2 = box
            whole_lines.append({'bbox': [x1, y1, x2, y2], 'left': x1, 'right': x2, 'width': x2 - x1, 'height': y2 - y1, 'component_count': len(group), 'baseline_y': float(row['center_y'])})
    whole_lines.sort(key=lambda r: (r['bbox'][1], r['bbox'][0]))
    return {'whole_lines': whole_lines, 'glyph_h_med': glyph_h_med}

def _et29d__et_step2_parent_extract_whole_lines(page_bgr, exclusions):
    ph, pw = page_bgr.shape[:2]
    gray = cv2.cvtColor(page_bgr, cv2.COLOR_BGR2GRAY)
    mask = np.ones((ph, pw), dtype=np.uint8) * 255
    for box in exclusions:
        x1, y1, x2, y2 = [int(v) for v in box]
        x1, y1 = (max(0, x1), max(0, y1))
        x2, y2 = (min(pw, x2), min(ph, y2))
        if x2 > x1 and y2 > y1:
            mask[y1:y2, x1:x2] = 0
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 15)
    binary[mask == 0] = 0
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
    comps = []
    for i in range(1, count):
        x = int(stats[i, cv2.CC_STAT_LEFT])
        y = int(stats[i, cv2.CC_STAT_TOP])
        cw = int(stats[i, cv2.CC_STAT_WIDTH])
        ch = int(stats[i, cv2.CC_STAT_HEIGHT])
        ca = int(stats[i, cv2.CC_STAT_AREA])
        if 2 <= ch <= ph * 0.055 and 1 <= cw <= pw * 0.1 and (ca >= 2):
            comps.append({'bbox': [x, y, x + cw, y + ch], 'cx': float(centroids[i][0]), 'cy': float(centroids[i][1])})
    if len(comps) < 10:
        return {'whole_lines': [], 'glyph_h_med': 1.0}
    heights = [c['bbox'][3] - c['bbox'][1] for c in comps]
    glyph_h_med = float(np.median(heights))
    baseline_tol = max(2.0, glyph_h_med * 0.7)
    rows = []
    for comp in sorted(comps, key=lambda c: (c['cy'], c['cx'])):
        best_idx, best_dist = (None, None)
        for idx, row in enumerate(rows):
            d = abs(comp['cy'] - row['center_y'])
            if d <= baseline_tol and (best_dist is None or d < best_dist):
                best_idx, best_dist = (idx, d)
        if best_idx is None:
            rows.append({'components': [comp], 'center_y': comp['cy']})
        else:
            rows[best_idx]['components'].append(comp)
            rows[best_idx]['center_y'] = float(np.median([c['cy'] for c in rows[best_idx]['components']]))
    whole_lines = []
    for row in rows:
        row_comps = sorted(row['components'], key=lambda c: c['bbox'][0])
        if len(row_comps) < 2:
            continue
        gaps = [b['bbox'][0] - a['bbox'][2] for a, b in zip(row_comps[:-1], row_comps[1:])]
        positive_gaps = [g for g in gaps if g >= 0]
        normal_gap = float(np.median(positive_gaps)) if positive_gaps else 0.0
        groups = [[row_comps[0]]]
        for prev, cur in zip(row_comps[:-1], row_comps[1:]):
            gap = cur['bbox'][0] - prev['bbox'][2]
            split_gap = gap > normal_gap + glyph_h_med * 3.0
            if split_gap:
                groups.append([cur])
            else:
                groups[-1].append(cur)
        for group in groups:
            if len(group) < 2:
                continue
            box = _et29d_union_box([c['bbox'] for c in group])
            if any((_et29d_boxes_intersect(box, ex) > 0 for ex in exclusions)):
                continue
            x1, y1, x2, y2 = box
            whole_lines.append({'bbox': [x1, y1, x2, y2], 'left': x1, 'right': x2, 'width': x2 - x1, 'height': y2 - y1, 'component_count': len(group), 'baseline_y': float(row['center_y'])})
    whole_lines.sort(key=lambda r: (r['bbox'][1], r['bbox'][0]))
    return {'whole_lines': whole_lines, 'glyph_h_med': glyph_h_med}

def _et29d_extract_whole_lines(page_bgr, exclusions):
    """
    Cumulative Step2 whole-line extractor.

    Parent extraction is untouched.

    When confirmed Visual exclusions exist, apply generic lane metadata
    before text-region grouping.
    """
    result = _et29d__et_step2_parent_extract_whole_lines(page_bgr, exclusions)
    if not isinstance(result, dict):
        return result
    whole_lines = list(result.get('whole_lines', []))
    if not exclusions:
        return result
    H, W = page_bgr.shape[:2]
    split_lines, decisions = _et29d_et_step2_split_lines_by_visual_and_corridor(whole_lines, exclusions, W)
    result = dict(result)
    result['whole_lines'] = split_lines
    result['step2_lane_decisions'] = decisions
    return result

def _et29d_et_step2_box_intersection(a, b):
    x1 = max(float(a[0]), float(b[0]))
    y1 = max(float(a[1]), float(b[1]))
    x2 = min(float(a[2]), float(b[2]))
    y2 = min(float(a[3]), float(b[3]))
    if x2 <= x1 or y2 <= y1:
        return 0.0
    return (x2 - x1) * (y2 - y1)

def _et29d_et_step2_line_inside_ratio(line_box, box):
    inter = _et29d_et_step2_box_intersection(line_box, box)
    la = max(1.0, (float(line_box[2]) - float(line_box[0])) * (float(line_box[3]) - float(line_box[1])))
    return inter / la

def _et29d_et_step2_vertical_corridor(lines, page_width, min_gap_ratio=0.045, min_side_lines=2):
    """
    STEP3 implementation.

    Detect a REAL persistent vertical whitespace corridor.

    Unlike Step2, this does not search pairwise line gaps.

    Method:
      1. project all text-line horizontal occupancy onto X;
      2. find X intervals crossed by very few text lines;
      3. require substantial text population on BOTH sides;
      4. prefer an interior corridor with strong persistence.

    Returns corridor midpoint or None.

    Generic geometry only.
    """
    if len(lines) < 4:
        return None
    W = max(1, int(round(float(page_width))))
    occupancy = np.zeros(W, dtype=np.int32)
    valid = []
    for ln in lines:
        b = ln['bbox']
        x1 = max(0, min(W - 1, int(np.floor(float(b[0])))))
        x2 = max(x1 + 1, min(W, int(np.ceil(float(b[2])))))
        occupancy[x1:x2] += 1
        valid.append((float(b[0]), float(b[2])))
    lo = int(round(W * 0.12))
    hi = int(round(W * 0.88))
    min_gap = max(8, int(round(W * min_gap_ratio)))
    max_cross = max(1, int(round(len(valid) * 0.08)))
    whiteish = occupancy <= max_cross
    runs = []
    start = None
    for x in range(lo, hi):
        if whiteish[x]:
            if start is None:
                start = x
        elif start is not None:
            if x - start >= min_gap:
                runs.append((start, x))
            start = None
    if start is not None:
        if hi - start >= min_gap:
            runs.append((start, hi))
    candidates = []
    for x1, x2 in runs:
        mid = (float(x1) + float(x2)) / 2.0
        left_count = sum((1 for a, b in valid if b <= x1))
        right_count = sum((1 for a, b in valid if a >= x2))
        crossing_count = sum((1 for a, b in valid if a < x2 and b > x1))
        if left_count < min_side_lines or right_count < min_side_lines:
            continue
        crossing_ratio = crossing_count / max(1, len(valid))
        if crossing_ratio > 0.15:
            continue
        width = x2 - x1
        balance = min(left_count, right_count) / max(left_count, right_count)
        score = float(width) * (0.5 + balance) * (1.0 - crossing_ratio)
        candidates.append({'x1': int(x1), 'x2': int(x2), 'mid': float(mid), 'width': int(width), 'left_count': int(left_count), 'right_count': int(right_count), 'crossing_count': int(crossing_count), 'crossing_ratio': float(crossing_ratio), 'score': float(score)})
    if not candidates:
        return None
    candidates.sort(key=lambda z: z['score'], reverse=True)
    return float(candidates[0]['mid'])

def _et29d_et_step2_split_lines_by_visual_and_corridor(whole_lines, visual_boxes, page_width):
    """
    STEP3 implementation.

    Physical segmentation BEFORE text grouping.

    Rules:
      A. lines physically inside confirmed Visual are removed;
      B. remaining lines are analysed in vertically-local windows;
      C. a persistent vertical whitespace corridor creates LEFT/RIGHT lanes;
      D. confirmed Visual acts as a physical obstacle:
         text cannot merge through its occupied X/Y space;
      E. full-width/crossing lines remain isolated rather than being forced
         into either lane.

    No page-specific coordinates.
    """
    text_lines = []
    for ln in whole_lines:
        lb = ln['bbox']
        inside_visual = False
        for vb in visual_boxes:
            if _et29d_et_step2_line_inside_ratio(lb, vb) >= 0.7:
                inside_visual = True
                break
        if not inside_visual:
            text_lines.append(dict(ln))
    if len(text_lines) < 4:
        return (text_lines, [])
    text_lines.sort(key=lambda z: (float(z['bbox'][1]), float(z['bbox'][0])))
    heights = [max(1.0, float(x['bbox'][3]) - float(x['bbox'][1])) for x in text_lines]
    med_h = statistics.median(heights) if heights else 7.0
    windows = []
    current = []
    current_bottom = None
    for ln in text_lines:
        b = ln['bbox']
        y1 = float(b[1])
        y2 = float(b[3])
        if not current:
            current = [ln]
            current_bottom = y2
            continue
        gap = y1 - float(current_bottom)
        if gap > med_h * 4.5:
            windows.append(current)
            current = [ln]
            current_bottom = y2
        else:
            current.append(ln)
            current_bottom = max(float(current_bottom), y2)
    if current:
        windows.append(current)
    output = []
    decisions = []
    for wi, window in enumerate(windows):
        corridor = _et29d_et_step2_vertical_corridor(window, float(page_width))
        if corridor is None:
            for ln in window:
                ln = dict(ln)
                ln['_et_lane'] = ln.get('_et_lane') or f'W{wi}_MAIN'
                output.append(ln)
            continue
        safety = max(2.0, float(page_width) * 0.008)
        left = []
        right = []
        crossing = []
        for ln in window:
            b = ln['bbox']
            x1 = float(b[0])
            x2 = float(b[2])
            if x2 <= corridor - safety:
                left.append(ln)
            elif x1 >= corridor + safety:
                right.append(ln)
            else:
                crossing.append(ln)
        crossing_ratio = len(crossing) / max(1, len(window))
        accepted = len(left) >= 2 and len(right) >= 2 and (crossing_ratio <= 0.18)
        decisions.append({'window': int(wi), 'corridor_x': round(float(corridor), 2), 'left_lines': len(left), 'right_lines': len(right), 'crossing_lines': len(crossing), 'crossing_ratio': round(float(crossing_ratio), 3), 'accepted': bool(accepted)})
        if not accepted:
            for ln in window:
                ln = dict(ln)
                ln['_et_lane'] = ln.get('_et_lane') or f'W{wi}_MAIN'
                output.append(ln)
            continue
        for ln in left:
            ln = dict(ln)
            ln['_et_lane'] = f'W{wi}_LEFT'
            output.append(ln)
        for ln in right:
            ln = dict(ln)
            ln['_et_lane'] = f'W{wi}_RIGHT'
            output.append(ln)
        for ci, ln in enumerate(crossing):
            ln = dict(ln)
            ln['_et_lane'] = f'W{wi}_CROSS_{ci}'
            output.append(ln)
    final = []
    for ln in output:
        ln = dict(ln)
        b = ln['bbox']
        lx1 = float(b[0])
        ly1 = float(b[1])
        lx2 = float(b[2])
        ly2 = float(b[3])
        for vi, vb in enumerate(visual_boxes):
            vx1, vy1, vx2, vy2 = [float(z) for z in vb]
            y_overlap = min(ly2, vy2) - max(ly1, vy1)
            if y_overlap <= 0:
                continue
            gap_left = vx1 - lx2
            gap_right = lx1 - vx2
            if gap_left > 0:
                ln['_et_visual_lane'] = f'V{vi}_LEFT'
            elif gap_right > 0:
                ln['_et_visual_lane'] = f'V{vi}_RIGHT'
            else:
                ln['_et_visual_lane'] = f'V{vi}_INTERSECT'
        final.append(ln)
    final.sort(key=lambda z: (float(z['bbox'][1]), float(z['bbox'][0])))
    return (final, decisions)

def _et29d_et_phys_bbox(obj):
    if obj is None:
        return None
    if isinstance(obj, (list, tuple)) and len(obj) == 4:
        return [int(x) for x in obj]
    for key in ('bbox', 'full_bbox', 'core_bbox'):
        b = obj.get(key) if isinstance(obj, dict) else None
        if b:
            return [int(x) for x in b]
    return None

def _et29d_et_phys_inter(a, b):
    if not a or not b:
        return 0
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))

def _et29d_et_phys_area(b):
    if not b:
        return 0
    return max(0, b[2] - b[0]) * max(0, b[3] - b[1])

def _et29d_et_phys_line_candidate_membership(lb, rb):
    """
    Return True when a RAW whole-line physically belongs to candidate rb.

    Use vertical centre + horizontal intersection.
    We intentionally do not require the whole line to fit inside rb because
    upstream boxes may already be geometrically wrong.
    """
    cy = 0.5 * (lb[1] + lb[3])
    if not rb[1] - 2 <= cy <= rb[3] + 2:
        return False
    xov = max(0, min(lb[2], rb[2]) - max(lb[0], rb[0]))
    lw = max(1, lb[2] - lb[0])
    return xov / lw >= 0.5

def _et29d_et_phys_line_inside_visual(lb, visual_boxes):
    """
    Confirmed Visual is a hard physical obstacle.
    Internal visual labels/caption must not become Text.
    """
    la = max(1, _et29d_et_phys_area(lb))
    for vb in visual_boxes:
        inter = _et29d_et_phys_inter(lb, vb)
        if inter / la >= 0.55:
            return True
    return False

def _et29d_et_phys_union_line_boxes(lines):
    boxes = [x['bbox'] for x in lines]
    return [min((b[0] for b in boxes)), min((b[1] for b in boxes)), max((b[2] for b in boxes)), max((b[3] for b in boxes))]

def _et29d_et_phys_find_internal_vertical_corridor(lines, candidate_box, glyph, page_w):
    """
    Find an INTERNAL persistent vertical whitespace corridor.

    Key distinction:
        ordinary spaces inside a sentence are NOT corridors because the
        whole-line box crosses them.

        A real two-island layout produces line boxes ending on the left
        and beginning again on the right, leaving an X interval crossed
        by almost no physical text lines.

    Returns:
        dict or None
    """
    if len(lines) < 4:
        return None
    x1, y1, x2, y2 = candidate_box
    width = max(1, x2 - x1)
    if width < max(8.0 * glyph, 0.2 * page_w):
        return None
    lo = int(round(x1 + 0.15 * width))
    hi = int(round(x2 - 0.15 * width))
    if hi <= lo:
        return None
    boundaries = set()
    for ln in lines:
        b = ln['bbox']
        if lo <= b[0] <= hi:
            boundaries.add(int(b[0]))
        if lo <= b[2] <= hi:
            boundaries.add(int(b[2]))
    if len(boundaries) < 2:
        return None
    boundaries = sorted(boundaries)
    candidates = []
    min_gap = max(2.0 * glyph, 0.025 * page_w, 10.0)
    for a, b in zip(boundaries[:-1], boundaries[1:]):
        gap = float(b - a)
        if gap < min_gap:
            continue
        mid = 0.5 * (a + b)
        left = []
        right = []
        crossing = []
        for ln in lines:
            lb = ln['bbox']
            moat = max(1.5, 0.2 * glyph)
            if lb[2] <= mid - moat:
                left.append(ln)
            elif lb[0] >= mid + moat:
                right.append(ln)
            else:
                crossing.append(ln)
        if len(left) < 2 or len(right) < 2:
            continue
        crossing_ratio = len(crossing) / max(1, len(lines))
        if crossing_ratio > 0.16:
            continue
        lb = _et29d_et_phys_union_line_boxes(left)
        rb = _et29d_et_phys_union_line_boxes(right)
        left_width = lb[2] - lb[0]
        right_width = rb[2] - rb[0]
        if left_width < 3.0 * glyph or right_width < 3.0 * glyph:
            continue
        balance = min(len(left), len(right)) / max(len(left), len(right))
        score = gap * (1.0 - crossing_ratio) * (0.65 + 0.35 * balance)
        candidates.append({'x_left': int(a), 'x_right': int(b), 'x_mid': float(mid), 'gap_width': float(gap), 'crossing_ratio': float(crossing_ratio), 'left': left, 'right': right, 'crossing': crossing, 'score': float(score)})
    if not candidates:
        return None
    candidates.sort(key=lambda z: z['score'], reverse=True)
    return candidates[0]

def _et29d_et_phys_split_candidate_once(region, whole_lines, visual_boxes, glyph, page_w):
    """
    Resolve one candidate into physical content islands.

    Returns:
        [region]          if no valid split
        [left, right...]  if physical corridor exists
    """
    rb = _et29d_et_phys_bbox(region)
    if not rb:
        return ([region], None)
    members = []
    for ln0 in whole_lines:
        ln = dict(ln0)
        lb = _et29d_et_phys_bbox(ln)
        if not lb:
            continue
        ln['bbox'] = lb
        if not _et29d_et_phys_line_candidate_membership(lb, rb):
            continue
        if _et29d_et_phys_line_inside_visual(lb, visual_boxes):
            continue
        members.append(ln)
    if len(members) < 4:
        return ([region], None)
    corridor = _et29d_et_phys_find_internal_vertical_corridor(members, rb, glyph, page_w)
    if corridor is None:
        return ([region], None)
    groups = [corridor['left'], corridor['right']]
    extras = []
    mid = corridor['x_mid']
    for ln in corridor['crossing']:
        b = ln['bbox']
        cx = 0.5 * (b[0] + b[2])
        if b[2] < mid:
            groups[0].append(ln)
        elif b[0] > mid:
            groups[1].append(ln)
        else:
            extras.append([ln])
    out = []
    for gi, group in enumerate(groups):
        if not group:
            continue
        box = _et29d_et_phys_union_line_boxes(group)
        nr = dict(region)
        nr['bbox'] = [int(x) for x in box]
        nr['line_count'] = len(group)
        nr['physical_resolver_rule'] = 'ET-PHYSICAL-WHITESPACE-ISLAND-RESOLVER-V1'
        nr['physical_parent_bbox'] = list(rb)
        nr['physical_corridor'] = [int(corridor['x_left']), int(corridor['x_right'])]
        nr['physical_island_index'] = gi
        nr['physical_crossing_ratio'] = round(corridor['crossing_ratio'], 4)
        for k in ('semantic_role', 'label', 'display_label'):
            nr.pop(k, None)
        out.append(nr)
    decision = {'source_bbox': rb, 'corridor': [int(corridor['x_left']), int(corridor['x_right'])], 'corridor_width': round(corridor['gap_width'], 2), 'crossing_ratio': round(corridor['crossing_ratio'], 4), 'result_boxes': [x['bbox'] for x in out], 'suppressed_crossing_groups': len(extras), 'suppressed_crossing_boxes': [_et29d_et_phys_union_line_boxes(g) for g in extras if g], 'rule': 'ET-PHYSICAL-WHITESPACE-ISLAND-RESOLVER-V1+CROSSING-DROP-V1'}
    return (out, decision)

def _et29d_et_phys_remove_text_visual_overlap(region, whole_lines, visual_boxes):
    """
    Final physical invariant.

    If a Text region overlaps a confirmed Visual, rebuild Text geometry only
    from its RAW whole-lines that are NOT Visual-internal.

    We never geometrically subtract a rectangle from text. We reconstruct
    from actual surviving content lines.
    """
    rb = _et29d_et_phys_bbox(region)
    if not rb:
        return (region, None)
    overlapping = [vb for vb in visual_boxes if _et29d_et_phys_inter(rb, vb) > 0]
    if not overlapping:
        return (region, None)
    surviving = []
    for ln0 in whole_lines:
        ln = dict(ln0)
        lb = _et29d_et_phys_bbox(ln)
        if not lb:
            continue
        ln['bbox'] = lb
        if not _et29d_et_phys_line_candidate_membership(lb, rb):
            continue
        if _et29d_et_phys_line_inside_visual(lb, visual_boxes):
            continue
        surviving.append(ln)
    if not surviving:
        nr = dict(region)
        nr['hold'] = True
        nr.setdefault('hold_reasons', []).append('TEXT_FULLY_OCCLUDED_BY_CONFIRMED_VISUAL')
        return (nr, {'source_bbox': rb, 'result_bbox': rb, 'rule': 'TEXT_VISUAL_OVERLAP_UNRESOLVED_HOLD'})
    new_box = _et29d_et_phys_union_line_boxes(surviving)
    nr = dict(region)
    nr['bbox'] = new_box
    nr['line_count'] = len(surviving)
    nr['physical_visual_exclusion_rule'] = 'CONFIRMED_VISUAL_HARD_OBSTACLE'
    return (nr, {'source_bbox': rb, 'result_bbox': new_box, 'rule': 'CONFIRMED_VISUAL_HARD_OBSTACLE'})

def _et29d_et_phys_resolve_regions(image, regions, visuals):
    """
    Generic final physical resolver.

    No page-specific coordinates.
    """
    H, W = image.shape[:2]
    visual_boxes = [_et29d_et_phys_bbox(v) for v in visuals if _et29d_et_phys_bbox(v)]
    lr = _et29d_extract_whole_lines(image, exclusions=[])
    whole_lines = [dict(x) for x in lr.get('whole_lines', [])]
    glyph = float(lr.get('glyph_h_med', 7) or 7)
    resolved = []
    decisions = []
    for r0 in regions:
        r = dict(r0)
        role = str(r.get('semantic_role', '')).upper()
        if role in ('TITLE', 'FORMULA', 'MARKER_TEXT'):
            resolved.append(r)
            continue
        r, vdec = _et29d_et_phys_remove_text_visual_overlap(r, whole_lines, visual_boxes)
        if vdec:
            decisions.append(vdec)
        current = [r]
        for depth in range(2):
            nxt = []
            changed = False
            for item in current:
                pieces, dec = _et29d_et_phys_split_candidate_once(item, whole_lines, visual_boxes, glyph, W)
                if dec and len(pieces) > 1:
                    changed = True
                    decisions.append(dec)
                nxt.extend(pieces)
            current = nxt
            if not changed:
                break
        resolved.extend(current)
    final = []
    for r in resolved:
        rb = _et29d_et_phys_bbox(r)
        overlap = any((_et29d_et_phys_inter(rb, vb) > 0 for vb in visual_boxes))
        if overlap:
            nr = dict(r)
            nr['hold'] = True
            nr.setdefault('hold_reasons', []).append('PHYSICAL_TEXT_VISUAL_OVERLAP')
            final.append(nr)
        else:
            final.append(r)
    final.sort(key=lambda r: (_et29d_et_phys_bbox(r)[1], _et29d_et_phys_bbox(r)[0]))
    return (final, decisions)


# ==================================================================================================
# ET-P29-AST-PHYSICAL-CLOSURE-V1
#
# Existing V4B gate/wrapper remains untouched.
# Only its private resolver target is rebound to the complete AST-renamed
# Oracle physical resolver.
# ==================================================================================================

_et29_et_phys_resolve_regions = _et29d_et_phys_resolve_regions

