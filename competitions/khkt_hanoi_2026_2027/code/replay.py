
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

import cv2
import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bbox(item):
    return item.get("bbox") or item.get("full_bbox") or item.get("core_bbox")


def area(b):
    return max(0, b[2]-b[0]) * max(0, b[3]-b[1])


def overlap(a, b):
    return (
        max(0, min(a[2],b[2])-max(a[0],b[0]))
        * max(0, min(a[3],b[3])-max(a[1],b[1]))
    )


def graphic_evidence(image, b):
    H, W = image.shape[:2]
    x1,y1,x2,y2 = map(int,b)
    crop = image[
        max(0,y1):min(H,y2),
        max(0,x1):min(W,x2)
    ]
    if crop.size == 0:
        return False, {}

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    colored = (
        (hsv[:,:,1] >= 55) &
        (hsv[:,:,2] >= 65)
    ).astype(np.uint8)

    _, _, stats, _ = cv2.connectedComponentsWithStats(colored, 8)
    components = sum(
        1 for x,y,w,h,a in stats[1:]
        if a >= 12 and w >= 4 and h >= 3
    )

    ink = (gray < 185).astype(np.uint8)*255
    hh, ww = ink.shape

    horizontal = cv2.morphologyEx(
        ink, cv2.MORPH_OPEN,
        cv2.getStructuringElement(
            cv2.MORPH_RECT, (max(12,ww//18),1)
        )
    )
    vertical = cv2.morphologyEx(
        ink, cv2.MORPH_OPEN,
        cv2.getStructuringElement(
            cv2.MORPH_RECT, (1,max(12,hh//7))
        )
    )

    hp = int(np.count_nonzero(horizontal))
    vp = int(np.count_nonzero(vertical))
    cf = float(colored.mean())

    # Trial criteria; not production-approved thresholds.
    protected = (
        cf >= .05 and components >= 20
        and hp >= 150 and vp >= 80
    )

    return protected, {
        "color_fraction": round(cf,5),
        "colored_components": components,
        "horizontal_stroke_pixels": hp,
        "vertical_stroke_pixels": vp,
    }


def ink_runs(image, region):
    x1,y1,x2,y2 = map(int,region)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    crop = gray[y1:min(y2,y1+110),x1:x2]
    active = (crop < 185).sum(axis=1) >= 3

    runs = []
    start = None
    for i, on in enumerate(list(active)+[False]):
        if on and start is None:
            start = i
        elif not on and start is not None:
            if runs and start-runs[-1][1] <= 2:
                runs[-1] = (runs[-1][0],i)
            else:
                runs.append((start,i))
            start = None
    return runs


def run(input_file, output_dir, code_dir):
    input_file = Path(input_file).resolve()
    output_dir = Path(output_dir).resolve()
    code_dir = Path(code_dir).resolve()

    output_dir.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(code_dir))

    spec = importlib.util.spec_from_file_location(
        "sourceguard_replay_base", code_dir/"pipeline.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    image = cv2.imread(str(input_file))
    assert image is not None, "HOLD_IMAGE_READ"
    H,W = image.shape[:2]

    original_signal = m._paragraph_geometry_signal
    gate_log = {}

    def gated_signal(box, lines):
        is_para, ev = original_signal(box, lines)
        if not is_para:
            return is_para, ev

        protected, g = graphic_evidence(image, box)
        gate_log[str(list(map(int,box)))] = {
            "protected": bool(protected), **g
        }
        if protected:
            ev = dict(ev)
            ev["experimental_graphic_gate"] = g
            return False, ev
        return is_para, ev

    # Patch only this process's in-memory module.
    m._paragraph_geometry_signal = gated_signal

    result = m.examtrust_run_page(
        image_path=str(input_file),
        page_ref="BIO12_P07",
        prev_context=None,
        output_dir=None,
        save_outputs=False
    )

    visuals = sorted(
        [dict(v) for v in result.get("visual_boxes",[])],
        key=lambda v:(bbox(v)[1],bbox(v)[0])
    )
    raw_texts = [
        dict(t) for t in result.get("text_regions",[])
    ]

    # Remove only strongly contained smaller Text duplicates.
    texts = []
    duplicates = []
    for i,t in enumerate(raw_texts):
        b=bbox(t)
        if not b or area(b)<=0:
            duplicates.append({"bbox":b,"reason":"INVALID"})
            continue

        duplicate = any(
            j!=i
            and bbox(parent) is not None
            and area(bbox(parent)) > 2*area(b)
            and overlap(b,bbox(parent))/max(1,area(b)) >= .90
            for j,parent in enumerate(raw_texts)
        )
        if duplicate:
            duplicates.append({"bbox":b,"reason":"CONTAINED"})
        else:
            texts.append(t)

    # Exclude page furniture and footer/source metadata from QG.
    body_texts=[]
    excluded=[]
    for t in texts:
        b=bbox(t)
        bh=(b[3]-b[1])/H
        bw=(b[2]-b[0])/W
        cy=(b[1]+b[3])/(2*H)

        furniture = (
            (b[3]/H < .045 and bh < .035)
            or (cy > .925 and bh < .065 and bw < .32)
            or (cy > .87 and bh < .035 and bw < .34)
        )
        if furniture:
            excluded.append({"bbox":b,"reason":"FURNITURE_OR_SOURCE"})
        else:
            body_texts.append(t)

    status = "HOLD"
    reasons=[]
    caption=None

    # This pilot expects two separately recognized figure components.
    # The rule does not use fixed image coordinates.
    if len(visuals)!=2:
        reasons.append("VISUAL_COUNT_NOT_TWO")
    if len(body_texts)!=2:
        reasons.append("TEXT_COUNT_NOT_TWO")

    vrecords=[]
    trecords=[]

    if not reasons:
        v1, v2 = visuals
        v1b=list(map(int,bbox(v1)))
        v2b=list(map(int,bbox(v2)))

        lower = [
            t for t in body_texts
            if bbox(t)[1] >= v2b[3]-20
        ]

        if len(lower)!=1:
            reasons.append("BODY_AFTER_V2_AMBIGUOUS")
        else:
            body_t=lower[0]
            b=list(map(int,bbox(body_t)))
            runs=ink_runs(image,b)

            if len(runs)<2:
                reasons.append("CAPTION_INK_LINES_NOT_FOUND")
            else:
                first,second=runs[0],runs[1]
                gap=second[0]-first[1]

                caption=[
                    b[0], b[1]+first[0],
                    b[2], b[1]+first[1]
                ]
                new_body=[
                    b[0],b[1]+second[0],
                    b[2],b[3]
                ]

                if gap<4:
                    reasons.append("CAPTION_BODY_GAP_TOO_SMALL")
                if caption[1]<v2b[3]:
                    reasons.append("CAPTION_ABOVE_V2_BOTTOM")
                if caption[3]>=new_body[1]:
                    reasons.append("CAPTION_BODY_OVERLAP")
                if new_body[1]>=new_body[3]:
                    reasons.append("EMPTY_BODY")

                # Caption is a geometric candidate. Verify with the
                # existing OCR helper before semantic attachment.
                try:
                    recognized = m.et_cw_ocr(
                        image,caption
                    ).strip()
                except Exception:
                    recognized = ""

                # Do not require OCR to be perfect: retain as review
                # evidence, but do not claim a semantic OCR pass.
                if not reasons:
                    full=[
                        min(v2b[0],caption[0]),
                        min(v2b[1],caption[1]),
                        max(v2b[2],caption[2]),
                        max(v2b[3],caption[3]),
                    ]

                    other=next(
                        t for t in body_texts if t is not body_t
                    )
                    t1b=list(map(int,bbox(other)))

                    vrecords=[
                        {
                            "id":"V1",
                            "core_bbox":v1b,
                            "full_bbox":v1b,
                            "semantic_role":"VISUAL"
                        },
                        {
                            "id":"V2",
                            "core_bbox":v2b,
                            "full_bbox":full,
                            "semantic_role":"VISUAL",
                            "caption":{
                                "bbox":caption,
                                "owner":"V2",
                                "ocr":recognized,
                                "status":"GEOMETRICALLY_ATTACHED"
                            },
                            "caption_lines":1
                        }
                    ]
                    trecords=[
                        {"id":"T1","bbox":t1b,
                         "semantic_role":"TEXT"},
                        {"id":"T2","bbox":new_body,
                         "semantic_role":"TEXT"}
                    ]

                    if any(
                        overlap(t["bbox"],v["full_bbox"])>0
                        for t in trecords for v in vrecords
                    ):
                        reasons.append("TEXT_VISUAL_OVERLAP")
                    if any(
                        overlap(t["bbox"],caption)>0
                        for t in trecords
                    ):
                        reasons.append("CAPTION_REMAINS_IN_TEXT")

    if not reasons:
        # Passing geometry is not production approval.
        status="PILOT_GEOMETRY_PASS_REVIEW_REQUIRED"

    payload={
        "schema":"SourceGuard_CrossSubject_Replay_v1",
        "status":status,
        "hold_reasons":reasons,
        "input_sha256":sha(input_file),
        "base_pipeline_sha256":sha(code_dir/"pipeline.py"),
        "base_engine_sha256":sha(code_dir/"sourceguard_engine.py"),
        "graphic_gate":gate_log,
        "visuals":vrecords,
        "text_regions":trecords,
        "removed_duplicates":duplicates,
        "excluded_furniture":excluded,
        "caption_candidate":caption,
        "question_generation_authorized":False,
        "physics_regression_verified":False,
        "production_approved":False,
    }

    (output_dir/"result.json").write_text(
        json.dumps(payload,ensure_ascii=False,indent=2),
        encoding="utf-8"
    )

    canvas=image.copy()

    for v in vrecords:
        b=v["full_bbox"]
        cv2.rectangle(
            canvas,(b[0],b[1]),(b[2],b[3]),(0,0,255),2
        )
        cv2.putText(
            canvas,v["id"],(b[0],max(18,b[1]-5)),
            cv2.FONT_HERSHEY_SIMPLEX,.6,(0,0,255),2
        )

    for t in trecords:
        b=t["bbox"]
        cv2.rectangle(
            canvas,(b[0],b[1]),(b[2],b[3]),(0,160,0),2
        )
        cv2.putText(
            canvas,t["id"],(b[0],max(18,b[1]-5)),
            cv2.FONT_HERSHEY_SIMPLEX,.6,(0,160,0),2
        )

    cv2.imwrite(str(output_dir/"overlay.png"),canvas)

    print("STATUS:",status)
    print("HOLD_REASONS:",reasons)
    print("VISUAL_COUNT:",len(vrecords))
    print("TEXT_COUNT:",len(trecords))
    print("CAPTION_OWNER:",
          vrecords[1]["caption"]["owner"] if len(vrecords)>1
          else "NONE")
    print("OUTPUT:",output_dir)

    return 0 if not reasons else 2


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--code-dir",required=True)
    args=parser.parse_args()
    sys.exit(run(args.input,args.output,args.code_dir))
