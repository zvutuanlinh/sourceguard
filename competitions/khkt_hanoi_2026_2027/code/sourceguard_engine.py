from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import uuid

BBox = Tuple[float, float, float, float]

class ObjectType(str, Enum):
    VISUAL = 'VISUAL'
    TEXT = 'TEXT'
    STRUCTURAL = 'STRUCTURAL'
    CONTAINER = 'CONTAINER'
    CAPTION = 'CAPTION'

class ObjectStatus(str, Enum):
    PROPOSED = 'PROPOSED'
    VALIDATED = 'VALIDATED'
    LOCKED = 'LOCKED'
    RENDERED = 'RENDERED'

@dataclass
class SourceObject:
    object_id: str
    object_type: ObjectType
    core_bbox: BBox
    confidence: float = 0.0
    status: ObjectStatus = ObjectStatus.PROPOSED
    parent_id: Optional[str] = None
    evidence: Dict = field(default_factory=dict)
    exclusion_bbox: Optional[BBox] = None
    caption_search_bbox: Optional[BBox] = None

@dataclass
class ReadingRegion:
    region_id: str
    object_ids: List[str]
    bbox: BBox

@dataclass
class Anchor:
    anchor_id: str
    object_id: str
    bbox: BBox

@dataclass
class ReadingLane:
    lane_id: str
    object_ids: List[str]

def make_id(prefix):
    return prefix + '-' + uuid.uuid4().hex[:12]


# ============================================================
# 1. Container
# ============================================================

def normalize_container(width, height):
    if width <= 0 or height <= 0:
        raise ValueError('Invalid container size')

    return {
        'width': int(width),
        'height': int(height),
        'aspect_ratio': float(width) / float(height)
    }


# ============================================================
# 2. Object
# ============================================================

def create_objects(candidates):
    objects = []

    for candidate in candidates:
        obj = SourceObject(
            object_id=make_id('OBJ'),
            object_type=ObjectType(candidate['type']),
            core_bbox=tuple(candidate['bbox']),
            confidence=float(candidate.get('confidence', 0.0)),
            parent_id=candidate.get('parent_id'),
            evidence=dict(candidate.get('evidence', {}))
        )

        objects.append(obj)

    return objects


# ============================================================
# 3. ReadingRegion
# ============================================================

def build_reading_regions(objects):
    regions = []

    for obj in objects:
        if obj.object_type in [
            ObjectType.TEXT,
            ObjectType.STRUCTURAL,
            ObjectType.CONTAINER
        ]:
            regions.append(
                ReadingRegion(
                    region_id=make_id('REG'),
                    object_ids=[obj.object_id],
                    bbox=obj.core_bbox
                )
            )

    return regions


# ============================================================
# 4. Anchor
# ============================================================

def detect_anchors(objects):
    anchors = []

    for obj in objects:
        if obj.object_type == ObjectType.STRUCTURAL:
            anchors.append(
                Anchor(
                    anchor_id=make_id('ANC'),
                    object_id=obj.object_id,
                    bbox=obj.core_bbox
                )
            )

    return anchors


# ============================================================
# 5. ReadingLane
# ============================================================

def build_reading_lanes(regions):
    lanes = []

    for region in regions:
        lanes.append(
            ReadingLane(
                lane_id=make_id('LANE'),
                object_ids=list(region.object_ids)
            )
        )

    return lanes


# ============================================================
# 6. RegionGrowing
# ============================================================

def grow_regions(regions, lanes):
    # Foundation implementation:
    # preserves verified region ownership.
    return regions


# ============================================================
# 7. Validation
# ============================================================

def _bbox_area(box):
    x1, y1, x2, y2 = box
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def _box_distance(a, b):

    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b

    dx = max(
        bx1 - ax2,
        ax1 - bx2,
        0.0
    )

    dy = max(
        by1 - ay2,
        ay1 - by2,
        0.0
    )

    return (
        dx * dx
        + dy * dy
    ) ** 0.5


def _intersection_over_smaller(a, b):

    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b

    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    iw = max(
        0.0,
        ix2 - ix1
    )

    ih = max(
        0.0,
        iy2 - iy1
    )

    inter = iw * ih

    smaller = min(
        _bbox_area(a),
        _bbox_area(b)
    )

    if smaller <= 0:
        return 0.0

    return inter / smaller


def _visual_validation_decision(
    obj,
    visual_objects,
    page_width,
    page_height
):

    box = obj.core_bbox

    x1, y1, x2, y2 = box

    w = max(
        1.0,
        x2 - x1
    )

    h = max(
        1.0,
        y2 - y1
    )

    page_area = max(
        1.0,
        page_width * page_height
    )

    area = _bbox_area(
        box
    )

    area_ratio = (
        area / page_area
    )

    aspect_ratio = (
        w / h
    )

    evidence = obj.evidence

    text_overlap = float(
        evidence.get(
            "text_overlap",
            0.0
        )
    )

    # --------------------------------------------------------
    # Generic Rule A:
    # paragraph-like wide strip dominated by OCR text
    # --------------------------------------------------------

    text_dominant_strip = (
        aspect_ratio >= 4.0
        and
        text_overlap >= 0.45
    )

    # --------------------------------------------------------
    # Generic Rule B:
    # very small candidate with substantial OCR text overlap
    # --------------------------------------------------------

    small_text_fragment = (
        area_ratio <= 0.004
        and
        text_overlap >= 0.35
    )

    # --------------------------------------------------------
    # Generic Rule C:
    # small fragment close to a much larger visual candidate
    # --------------------------------------------------------

    nearby_larger_visual = False

    if area_ratio <= 0.01:

        proximity_limit = (
            0.08
            *
            min(
                page_width,
                page_height
            )
        )

        for other in visual_objects:

            if other is obj:
                continue

            other_area = _bbox_area(
                other.core_bbox
            )

            if other_area < area * 4.0:
                continue

            distance = _box_distance(
                box,
                other.core_bbox
            )

            overlap = (
                _intersection_over_smaller(
                    box,
                    other.core_bbox
                )
            )

            if (
                distance <= proximity_limit
                or
                overlap >= 0.20
            ):

                nearby_larger_visual = True
                break

    if text_dominant_strip:

        return (
            False,
            "REJECT_TEXT_DOMINANT"
        )

    if (
        small_text_fragment
        and
        nearby_larger_visual
    ):

        return (
            False,
            "REJECT_TEXT_FRAGMENT_NEAR_VISUAL"
        )

    if small_text_fragment:

        return (
            False,
            "REJECT_SMALL_TEXT_FRAGMENT"
        )

    return (
        True,
        "KEEP_VISUAL"
    )


def validate_objects(
    objects,
    container=None
):

    # --------------------------------------------------------
    # Determine source extent.
    # Prefer actual Container dimensions when supplied.
    # Otherwise derive from current object geometry.
    # --------------------------------------------------------

    if container is not None:

        page_width = float(
            container["width"]
        )

        page_height = float(
            container["height"]
        )

    else:

        page_width = max(
            [
                float(
                    obj.core_bbox[2]
                )
                for obj in objects
            ]
            or [1.0]
        )

        page_height = max(
            [
                float(
                    obj.core_bbox[3]
                )
                for obj in objects
            ]
            or [1.0]
        )

    visual_objects = [
        obj
        for obj in objects
        if obj.object_type
        == ObjectType.VISUAL
    ]

    for obj in objects:

        # No evidence -> remain PROPOSED.
        if len(obj.evidence) <= 0:
            continue

        if (
            obj.object_type
            ==
            ObjectType.VISUAL
        ):

            keep, decision = (
                _visual_validation_decision(
                    obj,
                    visual_objects,
                    page_width,
                    page_height
                )
            )

            obj.evidence[
                "validation_decision"
            ] = decision

            if keep:

                obj.status = (
                    ObjectStatus.VALIDATED
                )

            # Rejected visual remains PROPOSED.
            # It is not eligible for lock/render.

        else:

            obj.status = (
                ObjectStatus.VALIDATED
            )

    return objects


def lock_visual(
    obj,
    exclusion_bbox=None,
    caption_search_bbox=None
):
    if obj.status != ObjectStatus.VALIDATED:
        raise RuntimeError(
            'NO_EXCLUSION_BEFORE_VALIDATION'
        )

    obj.exclusion_bbox = exclusion_bbox
    obj.caption_search_bbox = caption_search_bbox
    obj.status = ObjectStatus.LOCKED

    return obj


def validate_integrity(objects, regions, anchors, lanes):
    object_ids = [x.object_id for x in objects]

    duplicate_objects = (
        len(object_ids) != len(set(object_ids))
    )

    object_id_set = set(object_ids)

    invalid_region_refs = []

    for region in regions:
        for oid in region.object_ids:
            if oid not in object_id_set:
                invalid_region_refs.append(oid)

    invalid_anchor_refs = [
        anchor.object_id
        for anchor in anchors
        if anchor.object_id not in object_id_set
    ]

    invalid_lane_refs = []

    for lane in lanes:
        for oid in lane.object_ids:
            if oid not in object_id_set:
                invalid_lane_refs.append(oid)

    illegal_exclusion = [
        obj.object_id
        for obj in objects
        if (
            obj.exclusion_bbox is not None
            and obj.status == ObjectStatus.PROPOSED
        )
    ]

    return {
        'duplicate_objects': duplicate_objects,
        'invalid_region_refs': invalid_region_refs,
        'invalid_anchor_refs': invalid_anchor_refs,
        'invalid_lane_refs': invalid_lane_refs,
        'illegal_exclusion': illegal_exclusion,
        'pass': (
            not duplicate_objects
            and not invalid_region_refs
            and not invalid_anchor_refs
            and not invalid_lane_refs
            and not illegal_exclusion
        )
    }


# ============================================================
# 8. Render
# ============================================================

def render(objects, regions, anchors, lanes):
    for obj in objects:
        if obj.status in [
            ObjectStatus.VALIDATED,
            ObjectStatus.LOCKED
        ]:
            obj.status = ObjectStatus.RENDERED

    return {
        'object_count': len(objects),
        'region_count': len(regions),
        'anchor_count': len(anchors),
        'lane_count': len(lanes),
        'object_ids': [
            x.object_id for x in objects
        ]
    }

# === SOURCEGUARD_VISUAL_RULESET_V2_PROMOTED ===
#
# Promoted only after:
#   PAGE08 regression PASS
#   PAGE91 V7 regression PASS
#
# Architecture remains:
# Container -> Object -> ReadingRegion -> Anchor ->
# ReadingLane -> RegionGrowing -> Validation -> Render
#
# These are helper semantics, NOT new pipeline stages.


def _sgv2_width(b):
    return max(1, b[2] - b[0])


def _sgv2_height(b):
    return max(1, b[3] - b[1])


def _sgv2_union(boxes):
    boxes = [
        list(map(int, b))
        for b in boxes
        if b is not None
    ]

    if not boxes:
        return None

    return [
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    ]


def _sgv2_x_overlap_ratio(a, b):

    inter = max(
        0,
        min(a[2], b[2])
        -
        max(a[0], b[0])
    )

    return (
        inter
        /
        max(
            1,
            min(
                _sgv2_width(a),
                _sgv2_width(b)
            )
        )
    )


def _sgv2_center_x(b):
    return (
        b[0] + b[2]
    ) / 2.0


def _sgv2_is_paragraph_like(
    text_item,
    page_width
):

    bbox = text_item.get(
        "bbox"
    )

    if not bbox:
        return False

    text = str(
        text_item.get(
            "text",
            ""
        )
    ).strip()

    words = [
        x
        for x in text.split()
        if x
    ]

    width_ratio = (
        _sgv2_width(bbox)
        /
        max(
            1,
            page_width
        )
    )

    return (
        len(words) >= 8
        and
        width_ratio >= 0.35
    )


def visual_ruleset_v2_group_candidates(
    visual_objects
):
    """
    Generic sibling visual grouping.

    Rule:
      - compatible vertical placement
      - reasonable horizontal distance
      - no page-specific coordinates

    Returns logical group records only.
    Does not alter child core bboxes.
    """

    items = []

    for obj in visual_objects:

        bbox = getattr(
            obj,
            "core_bbox",
            None
        )

        if bbox is None:
            continue

        items.append(
            {
                "object":
                    obj,
                "bbox":
                    list(
                        map(
                            int,
                            bbox
                        )
                    )
            }
        )

    groups = []
    used = set()

    for i, a in enumerate(items):

        if i in used:
            continue

        members = [
            i
        ]

        for j in range(
            i + 1,
            len(items)
        ):

            if j in used:
                continue

            b = items[j]

            ab = a[
                "bbox"
            ]

            bb = b[
                "bbox"
            ]

            vertical_overlap = max(
                0,
                min(
                    ab[3],
                    bb[3]
                )
                -
                max(
                    ab[1],
                    bb[1]
                )
            )

            vertical_ratio = (
                vertical_overlap
                /
                max(
                    1,
                    min(
                        _sgv2_height(
                            ab
                        ),
                        _sgv2_height(
                            bb
                        )
                    )
                )
            )

            horizontal_gap = max(
                bb[0] - ab[2],
                ab[0] - bb[2],
                0
            )

            ref_width = (
                _sgv2_width(
                    ab
                )
                +
                _sgv2_width(
                    bb
                )
            ) / 2.0

            if (
                vertical_ratio >= 0.55
                and
                horizontal_gap
                <=
                0.45 * ref_width
            ):
                members.append(
                    j
                )

        if len(
            members
        ) >= 2:

            boxes = [
                items[k][
                    "bbox"
                ]
                for k
                in members
            ]

            groups.append(
                {
                    "members":
                        [
                            items[k][
                                "object"
                            ]
                            for k
                            in members
                        ],

                    "container_bbox":
                        _sgv2_union(
                            boxes
                        ),
                }
            )

            used.update(
                members
            )

    return groups


def visual_ruleset_v2_caption_chain(
    core_bbox,
    text_items,
    page_width,
    page_height,
    max_lines=3
):
    """
    Canonical V7 caption behavior.

    - validated visual core first
    - local text items only
    - paragraph-like rejected
    - first caption line must be close below visual
    - max 3 contiguous lines
    - whitespace break stops immediately
    """

    core = list(
        map(
            int,
            core_bbox
        )
    )

    candidates = []

    for item in text_items:

        bbox = item.get(
            "bbox"
        )

        if bbox is None:
            continue

        bbox = list(
            map(
                int,
                bbox
            )
        )

        text = str(
            item.get(
                "text",
                ""
            )
        ).strip()

        words = [
            x
            for x in text.split()
            if x
        ]

        width_ratio_page = (
            _sgv2_width(
                bbox
            )
            /
            max(
                1,
                page_width
            )
        )

        paragraph_like = (
            len(
                words
            ) >= 8
            and
            width_ratio_page >= 0.35
        )

        if paragraph_like:
            continue

        gap = (
            bbox[1]
            -
            core[3]
        )

        if gap < -3:
            continue

        if gap > (
            0.055
            *
            page_height
        ):
            continue

        overlap = (
            _sgv2_x_overlap_ratio(
                core,
                bbox
            )
        )

        center_delta = abs(
            _sgv2_center_x(
                core
            )
            -
            _sgv2_center_x(
                bbox
            )
        )

        center_ratio = (
            center_delta
            /
            max(
                1,
                _sgv2_width(
                    core
                )
            )
        )

        if (
            overlap < 0.20
            and
            center_ratio > 0.60
        ):
            continue

        if (
            _sgv2_width(
                bbox
            )
            >
            1.35
            *
            _sgv2_width(
                core
            )
        ):
            continue

        candidate = dict(
            item
        )

        candidate[
            "bbox"
        ] = bbox

        candidate[
            "gap"
        ] = gap

        candidates.append(
            candidate
        )

    candidates.sort(
        key=lambda x: (
            x[
                "bbox"
            ][1],
            x[
                "bbox"
            ][0]
        )
    )

    attached = []

    if not candidates:
        return attached

    first = candidates[0]

    if (
        first[
            "gap"
        ]
        >
        0.035
        *
        page_height
    ):
        return attached

    attached.append(
        first
    )

    previous = first

    for candidate in candidates[1:]:

        if len(
            attached
        ) >= max_lines:
            break

        vertical_gap = (
            candidate[
                "bbox"
            ][1]
            -
            previous[
                "bbox"
            ][3]
        )

        average_height = (
            _sgv2_height(
                previous[
                    "bbox"
                ]
            )
            +
            _sgv2_height(
                candidate[
                    "bbox"
                ]
            )
        ) / 2.0

        # Canonical V7 hard whitespace stop.
        if (
            vertical_gap
            >
            0.85
            *
            average_height
        ):
            break

        if (
            vertical_gap
            >
            0.014
            *
            page_height
        ):
            break

        # Keep caption chain spatially continuous.
        overlap_prev = (
            _sgv2_x_overlap_ratio(
                previous[
                    "bbox"
                ],
                candidate[
                    "bbox"
                ]
            )
        )

        center_delta_prev = abs(
            _sgv2_center_x(
                previous[
                    "bbox"
                ]
            )
            -
            _sgv2_center_x(
                candidate[
                    "bbox"
                ]
            )
        )

        reference_width = max(
            1,
            min(
                _sgv2_width(
                    previous[
                        "bbox"
                    ]
                ),
                _sgv2_width(
                    candidate[
                        "bbox"
                    ]
                )
            )
        )

        if (
            overlap_prev < 0.20
            and
            center_delta_prev
            >
            0.45
            *
            reference_width
        ):
            break

        attached.append(
            candidate
        )

        previous = candidate

    return attached

def visual_ruleset_v2_local_grow(
    core_bbox,
    text_items,
    page_width,
    page_height,
    sibling_core_bboxes=None,
    group_label_bbox=None
):
    """
    Canonical V7 local object grow.

    Exactly the proven behavior:
    - local only
    - paragraph rejection
    - sibling ownership protection
    - group-label protection
    - caption detected separately
    - caption cannot also remain annotation
    """

    core = list(
        map(
            int,
            core_bbox
        )
    )

    sibling_core_bboxes = (
        sibling_core_bboxes
        or
        []
    )

    caption_candidates = []

    annotation_candidates = []

    for item in text_items:

        bbox = item.get(
            "bbox"
        )

        if bbox is None:
            continue

        bbox = list(
            map(
                int,
                bbox
            )
        )

        text = str(
            item.get(
                "text",
                ""
            )
        ).strip()

        words = [
            x
            for x in text.split()
            if x
        ]

        width_ratio_page = (
            _sgv2_width(
                bbox
            )
            /
            max(
                1,
                page_width
            )
        )

        paragraph_like = (
            len(
                words
            ) >= 8
            and
            width_ratio_page >= 0.35
        )

        if paragraph_like:
            continue

        # --------------------------------------------
        # Shared group label belongs to group only.
        # --------------------------------------------

        if group_label_bbox is not None:

            if (
                _sgv2_x_overlap_ratio(
                    bbox,
                    group_label_bbox
                )
                > 0.50
                and
                abs(
                    bbox[1]
                    -
                    group_label_bbox[1]
                )
                <
                0.025
                *
                page_height
            ):
                continue

        # --------------------------------------------
        # Sibling ownership protection.
        # --------------------------------------------

        own_gap_x = abs(
            _sgv2_center_x(
                bbox
            )
            -
            _sgv2_center_x(
                core
            )
        )

        belongs_to_sibling = False

        for sibling in sibling_core_bboxes:

            sibling_gap_x = abs(
                _sgv2_center_x(
                    bbox
                )
                -
                _sgv2_center_x(
                    sibling
                )
            )

            if sibling_gap_x < own_gap_x:

                belongs_to_sibling = True
                break

        if belongs_to_sibling:
            continue

        # --------------------------------------------
        # Caption candidate first.
        # This mirrors V7: caption is separated from
        # annotation BEFORE full-object union.
        # --------------------------------------------

        gap_down = (
            bbox[1]
            -
            core[3]
        )

        overlap = (
            _sgv2_x_overlap_ratio(
                core,
                bbox
            )
        )

        center_ratio = (
            abs(
                _sgv2_center_x(
                    bbox
                )
                -
                _sgv2_center_x(
                    core
                )
            )
            /
            max(
                1,
                _sgv2_width(
                    core
                )
            )
        )

        if (
            gap_down >= -2
            and
            gap_down
            <=
            0.16
            *
            page_height
            and
            (
                overlap >= 0.15
                or
                center_ratio <= 0.60
            )
        ):

            c = dict(
                item
            )

            c[
                "bbox"
            ] = bbox

            c[
                "gap"
            ] = gap_down

            caption_candidates.append(
                c
            )

            # Important:
            # a caption candidate is NOT annotation.
            continue

        # --------------------------------------------
        # Figure-associated annotation.
        # --------------------------------------------

        if len(
            words
        ) > 6:
            continue

        if (
            _sgv2_width(
                bbox
            )
            >
            1.15
            *
            _sgv2_width(
                core
            )
        ):
            continue

        dx = max(
            core[0] - bbox[2],
            bbox[0] - core[2],
            0
        )

        dy = max(
            core[1] - bbox[3],
            bbox[1] - core[3],
            0
        )

        distance = (
            dx * dx
            +
            dy * dy
        ) ** 0.5

        max_distance = max(
            0.30
            *
            _sgv2_width(
                core
            ),
            0.30
            *
            _sgv2_height(
                core
            )
        )

        if distance <= max_distance:

            a = dict(
                item
            )

            a[
                "bbox"
            ] = bbox

            annotation_candidates.append(
                a
            )

    # --------------------------------------------
    # Canonical V7 caption chain.
    # --------------------------------------------

    caption_candidates.sort(
        key=lambda x: (
            x[
                "bbox"
            ][1],
            x[
                "bbox"
            ][0]
        )
    )

    local_caption = []

    if caption_candidates:

        first = caption_candidates[0]

        if (
            first[
                "gap"
            ]
            <=
            0.08
            *
            page_height
        ):

            local_caption.append(
                first
            )

            previous = first

            for candidate in caption_candidates[1:]:

                if len(
                    local_caption
                ) >= 3:
                    break

                vertical_gap = (
                    candidate[
                        "bbox"
                    ][1]
                    -
                    previous[
                        "bbox"
                    ][3]
                )

                average_height = (
                    _sgv2_height(
                        previous[
                            "bbox"
                        ]
                    )
                    +
                    _sgv2_height(
                        candidate[
                            "bbox"
                        ]
                    )
                ) / 2.0

                if (
                    vertical_gap
                    >
                    0.85
                    *
                    average_height
                ):
                    break

                if (
                    vertical_gap
                    >
                    0.014
                    *
                    page_height
                ):
                    break

                overlap_prev = (
                    _sgv2_x_overlap_ratio(
                        previous[
                            "bbox"
                        ],
                        candidate[
                            "bbox"
                        ]
                    )
                )

                center_delta_prev = abs(
                    _sgv2_center_x(
                        previous[
                            "bbox"
                        ]
                    )
                    -
                    _sgv2_center_x(
                        candidate[
                            "bbox"
                        ]
                    )
                )

                reference_width = max(
                    1,
                    min(
                        _sgv2_width(
                            previous[
                                "bbox"
                            ]
                        ),
                        _sgv2_width(
                            candidate[
                                "bbox"
                            ]
                        )
                    )
                )

                if (
                    overlap_prev < 0.20
                    and
                    center_delta_prev
                    >
                    0.45
                    *
                    reference_width
                ):
                    break

                local_caption.append(
                    candidate
                )

                previous = candidate

    boxes = [
        core
    ]

    boxes.extend(
        item[
            "bbox"
        ]
        for item
        in annotation_candidates
    )

    boxes.extend(
        item[
            "bbox"
        ]
        for item
        in local_caption
    )

    return {
        "core_bbox":
            core,

        "associated_text":
            annotation_candidates,

        "local_caption":
            local_caption,

        "full_object_bbox":
            _sgv2_union(
                boxes
            ),
    }

def sourceguard_visual_ruleset_version():
    """
    Runtime identity only.
    """

    return {
        "ruleset_id":
            "SOURCEGUARD_VISUAL_RULESET_V2",

        "version":
            "2.0.0",

        "promotion_state":
            "PROMOTED_AFTER_PAGE08_PAGE91_REGRESSION",

        "architecture_changed":
            False,

        "gold_modified":
            False,
    }

# === END SOURCEGUARD_VISUAL_RULESET_V2_PROMOTED ===
