# ExamTrust AI — Run from a Blank Colab

Run one command:

```python
!python /content/drive/MyDrive/SourceGuard_Git/sourceguard/code/examtrust_btc_p06_p07_p08_pipeline_from_raw.py --mode btc-replay
```

Expected:

```text
RESULT = PASS / RAW_TO_READY_FOR_USE_PIPELINE_VERIFIED
```

Pipeline:

RAW P06/P07/P08 -> Source Units -> Human Selection -> Composition -> Question Contract -> Pregen -> Candidate V1 fail -> Candidate V2 -> Postgen PASS -> Teacher APPROVED -> READY_FOR_USE.

BTC replay does not call Gemini, OCR, or segmentation live.

Each execution creates a new reproducibility run under:

`EXAMTRUST_BTC_FINAL_ISOLATED_V1/07_REPRO_RUNS/`
