"""
SourceGuard Frozen Source Retrieval Runtime

Source truth:
    original source page
    + SHA256
    + frozen geometry components

This module:
    - reads frozen runtime index
    - retrieves source units and content chains
    - verifies original source SHA
    - extracts exact frozen components

This module does NOT:
    - OCR
    - detect objects
    - modify geometry
    - modify Gold
    - modify frozen artifacts
"""

from pathlib import Path
from collections import defaultdict
import json
import hashlib

import cv2
import numpy as np


class SourceGuardError(RuntimeError):
    pass


class SourceGuardRuntime:

    def __init__(self, repo_root):

        self.repo_root = Path(
            repo_root
        )

        self.units_file = (
            self.repo_root
            / "source_index/source_units.jsonl"
        )

        self.chains_file = (
            self.repo_root
            / "source_index/content_chains.jsonl"
        )

        self.manifest_file = (
            self.repo_root
            / "source_index/index_manifest.json"
        )

        self._page_cache = {}

        self._load()


    # --------------------------------------------------------
    # BASIC HELPERS
    # --------------------------------------------------------

    @staticmethod
    def sha256_file(path):

        h = hashlib.sha256()

        with Path(path).open("rb") as f:

            for chunk in iter(
                lambda: f.read(1024 * 1024),
                b""
            ):
                h.update(chunk)

        return h.hexdigest()


    @staticmethod
    def load_jsonl(path):

        rows = []

        with Path(path).open(
            "r",
            encoding="utf-8"
        ) as f:

            for line in f:

                line = line.strip()

                if line:
                    rows.append(
                        json.loads(line)
                    )

        return rows


    # --------------------------------------------------------
    # LOAD FROZEN INDEX
    # --------------------------------------------------------

    def _load(self):

        for path in [
            self.units_file,
            self.chains_file,
            self.manifest_file,
        ]:

            if not path.exists():
                raise SourceGuardError(
                    f"Missing runtime file: {path}"
                )


        self.manifest = json.loads(
            self.manifest_file.read_text(
                encoding="utf-8"
            )
        )


        if self.manifest.get("state") != "FROZEN":

            raise SourceGuardError(
                "Runtime index is not FROZEN"
            )


        if (
            self.sha256_file(
                self.units_file
            )
            !=
            self.manifest[
                "source_units_sha256"
            ]
        ):

            raise SourceGuardError(
                "source_units SHA mismatch"
            )


        if (
            self.sha256_file(
                self.chains_file
            )
            !=
            self.manifest[
                "content_chains_sha256"
            ]
        ):

            raise SourceGuardError(
                "content_chains SHA mismatch"
            )


        self.source_units = (
            self.load_jsonl(
                self.units_file
            )
        )

        self.content_chains = (
            self.load_jsonl(
                self.chains_file
            )
        )


        self.source_by_id = {
            x["source_id"]: x
            for x in self.source_units
        }

        self.chain_by_id = {
            x["content_chain_id"]: x
            for x in self.content_chains
        }


        if (
            len(self.source_by_id)
            !=
            len(self.source_units)
        ):

            raise SourceGuardError(
                "Duplicate source_id"
            )


        if (
            len(self.chain_by_id)
            !=
            len(self.content_chains)
        ):

            raise SourceGuardError(
                "Duplicate content_chain_id"
            )


    # --------------------------------------------------------
    # METADATA LOOKUP
    # --------------------------------------------------------

    def get_source(
        self,
        source_id
    ):

        if source_id not in self.source_by_id:

            raise KeyError(
                f"Unknown source_id: {source_id}"
            )

        return self.source_by_id[
            source_id
        ]


    def get_chain(
        self,
        content_chain_id
    ):

        if content_chain_id not in self.chain_by_id:

            raise KeyError(
                "Unknown content_chain_id: "
                + content_chain_id
            )


        chain = self.chain_by_id[
            content_chain_id
        ]


        members = [
            self.get_source(
                source_id
            )
            for source_id
            in chain["source_ids"]
        ]


        return sorted(
            members,
            key=lambda x: (
                x["page_ref"],
                x["box_id"]
            )
        )


    def find_sources(
        self,
        *,
        context=None,
        page=None,
        type_code=None
    ):

        rows = self.source_units


        if context is not None:

            rows = [
                x for x in rows
                if x["context_code"]
                == context
            ]


        if page is not None:

            rows = [
                x for x in rows
                if x["page_ref"]
                == page
            ]


        if type_code is not None:

            rows = [
                x for x in rows
                if x["type_code"]
                == type_code
            ]


        return list(rows)


    # --------------------------------------------------------
    # VERIFIED ORIGINAL PAGE
    # --------------------------------------------------------

    def load_verified_page(
        self,
        source
    ):

        path = Path(
            source[
                "source_page_path"
            ]
        )


        if not path.exists():

            raise SourceGuardError(
                f"Missing source page: {path}"
            )


        key = str(path)


        if key not in self._page_cache:

            actual_sha = (
                self.sha256_file(
                    path
                )
            )


            expected_sha = source[
                "source_page_sha256"
            ]


            if actual_sha != expected_sha:

                raise SourceGuardError(
                    "Source page SHA mismatch: "
                    + str(path)
                )


            image = cv2.imread(
                str(path)
            )


            if image is None:

                raise SourceGuardError(
                    "Cannot decode source image: "
                    + str(path)
                )


            self._page_cache[key] = {
                "sha256": actual_sha,
                "image": image,
            }


        return self._page_cache[
            key
        ]["image"]


    # --------------------------------------------------------
    # EXACT FROZEN COMPONENT EXTRACTION
    # --------------------------------------------------------

    def extract_components(
        self,
        source_id
    ):

        source = self.get_source(
            source_id
        )

        image = self.load_verified_page(
            source
        )

        H, W = image.shape[:2]

        output = []


        for index, bbox in enumerate(
            source["components"],
            start=1
        ):

            x1,y1,x2,y2 = [
                int(v)
                for v in bbox
            ]


            if not (
                0 <= x1 < x2 <= W
                and
                0 <= y1 < y2 <= H
            ):

                raise SourceGuardError(
                    f"Invalid frozen geometry "
                    f"{source_id} component "
                    f"{index}: {bbox}"
                )


            # EXACT geometry.
            # No padding.
            # No resize.
            crop = image[
                y1:y2,
                x1:x2
            ].copy()


            if crop.size == 0:

                raise SourceGuardError(
                    "Empty extracted component: "
                    f"{source_id}/{index}"
                )


            output.append({
                "component_index":
                    index,

                "bbox":
                    [x1,y1,x2,y2],

                "image":
                    crop,
            })


        return output


    # --------------------------------------------------------
    # SOURCE CARD
    # --------------------------------------------------------

    def build_source_card(
        self,
        source_id,
        *,
        label_height=22,
        component_gap=4
    ):
        """
        Human-facing VIEW only.

        Label is outside source content.
        Exact component crops remain unchanged.
        """

        source = self.get_source(
            source_id
        )

        crops = self.extract_components(
            source_id
        )


        max_width = max(
            c["image"].shape[1]
            for c in crops
        )


        body_height = sum(
            c["image"].shape[0]
            for c in crops
        )


        body_height += (
            component_gap
            *
            max(
                0,
                len(crops)-1
            )
        )


        card = np.full(
            (
                label_height
                +
                body_height,

                max_width,

                3
            ),
            255,
            dtype=np.uint8
        )


        # label outside source
        label = source[
            "display_label"
        ]

        font = cv2.FONT_HERSHEY_DUPLEX
        scale = 0.33
        thickness = 1


        (_, text_h), _ = cv2.getTextSize(
            label,
            font,
            scale,
            thickness
        )


        cv2.putText(
            card,
            label,
            (
                2,
                min(
                    label_height - 4,
                    text_h + 5
                )
            ),
            font,
            scale,
            (0,0,0),
            thickness,
            cv2.LINE_AA
        )


        y = label_height


        for index,item in enumerate(
            crops
        ):

            crop = item[
                "image"
            ]

            h,w = crop.shape[:2]


            card[
                y:y+h,
                0:w
            ] = crop


            y += h


            if index < len(crops)-1:
                y += component_gap


        return {
            "source":
                source,

            "components":
                crops,

            "card":
                card,
        }


    # --------------------------------------------------------
    # COMPLETE CHAIN EXTRACTION
    # --------------------------------------------------------

    def extract_chain(
        self,
        content_chain_id
    ):

        members = self.get_chain(
            content_chain_id
        )


        return [
            self.build_source_card(
                member["source_id"]
            )
            for member in members
        ]


    # --------------------------------------------------------
    # RUNTIME SUMMARY
    # --------------------------------------------------------

    def summary(self):

        return {
            "state":
                self.manifest["state"],

            "source_units":
                len(self.source_units),

            "content_chains":
                len(self.content_chains),

            "source_units_sha256":
                self.manifest[
                    "source_units_sha256"
                ],

            "content_chains_sha256":
                self.manifest[
                    "content_chains_sha256"
                ],
        }
