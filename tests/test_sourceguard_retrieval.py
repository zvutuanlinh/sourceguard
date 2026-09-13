from pathlib import Path
import sys

REPO = Path(
    "/content/drive/MyDrive/SourceGuard_Git/sourceguard"
)

sys.path.insert(
    0,
    str(REPO / "code")
)

from sourceguard_retrieval import SourceGuardRuntime


def test_runtime():

    rt = SourceGuardRuntime(
        REPO
    )

    summary = rt.summary()

    assert summary["state"] == "FROZEN"

    assert summary[
        "source_units"
    ] == 13

    assert summary[
        "content_chains"
    ] == 13


    # --------------------------------------------------------
    # Exact source metadata
    # --------------------------------------------------------

    r03 = rt.get_source(
        "PHY12_P91_R03"
    )

    assert (
        r03["display_label"]
        ==
        "B21|P91|R03|TN"
    )

    assert (
        r03["components"]
        ==
        [
            [49,190,318,372],
            [62,369,452,411]
        ]
    )


    # --------------------------------------------------------
    # Title-only excluded
    # --------------------------------------------------------

    assert (
        "PHY12_P91_R01"
        not in rt.source_by_id
    )


    # --------------------------------------------------------
    # Chain retrieval
    # --------------------------------------------------------

    chain = rt.get_chain(
        "PHY12_B21_R07_CHAIN"
    )

    assert len(chain) == 1

    assert (
        chain[0]["source_id"]
        ==
        "PHY12_P91_R07"
    )


    # --------------------------------------------------------
    # Type query
    # --------------------------------------------------------

    visuals = rt.find_sources(
        context="B21",
        type_code="H"
    )

    assert len(visuals) == 3


    # --------------------------------------------------------
    # Actual frozen extraction
    # --------------------------------------------------------

    crops = rt.extract_components(
        "PHY12_P91_R03"
    )

    assert len(crops) == 2

    assert (
        crops[0]["bbox"]
        ==
        [49,190,318,372]
    )

    assert (
        crops[1]["bbox"]
        ==
        [62,369,452,411]
    )


    # --------------------------------------------------------
    # Source card
    # --------------------------------------------------------

    card = rt.build_source_card(
        "PHY12_P91_R03"
    )

    assert (
        card["source"]["source_id"]
        ==
        "PHY12_P91_R03"
    )

    assert card["card"].size > 0


if __name__ == "__main__":

    test_runtime()

    print(
        "SOURCEGUARD RETRIEVAL TEST: PASS"
    )
