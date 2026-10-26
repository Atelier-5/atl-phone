<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Atelier-5 -->
<!-- What atl-phone is licensed under, and the licences of everything it ships, fetches or runs on. -->

# Licensing

**atl-phone is licensed under the GNU GPL v3.0 or later** (see `LICENSE`). Copyright (C) 2026 Atelier-5.

The name "Atelier-5" and its logos are not licensed for use by modified versions (GPLv3 section 7(e));
see [atl-hub/TRADEMARKS.md](https://github.com/Atelier-5/atl-hub/blob/main/TRADEMARKS.md).

Everything below is free software or openly licensed, and compatible with distributing atl-phone under the GPL v3:
Apache-2.0, MIT, BSD and MPL-2.0 code can be combined with GPL v3 code, and the models and fonts are separate works
with their own permissive licences.

## Shipped in this repository

| What | Licence | Notice |
|---|---|---|
| Face-API 1.7.15 with TensorFlow.js 4.22.0, and its models | MIT; Apache-2.0 | `ros2/atl_phone/web/vendor/README.md` |
| MediaPipe Tasks Vision 0.10.14 and its models | Apache-2.0 | same |
| js-aruco2 2.0.0 (its dictionary from OpenCV) | MIT (BSD-3-Clause) | same |
| Tesseract.js 5.1.1, its core and the deu/eng/fra data | Apache-2.0 | same |
| QR Code Generator 1.4.4 | MIT | same |
| The architecture pack's pages: the Archify viewer and the JetBrains Mono font they embed | MIT; OFL-1.1 | `docs/architecture/NOTICE.md` |

## Fetched, not shipped

| What | Licence | Where |
|---|---|---|
| Vosk small German and French models | Apache-2.0 | `scripts/get_models.sh`, `models/README.md` |
| Opus-MT de-fr and fr-de (Helsinki-NLP), converted to CTranslate2 | Apache-2.0 on their model cards; the OPUS-MT project releases its models under CC-BY-4.0, so credit "OPUS-MT, Helsinki-NLP" either way | same |
| Webots' Thymio II PROTO, loaded by the worlds from Cyberbotics' R2025a repository | Apache-2.0 | `webots/protos/` |

## Built into the image or run beside it (not redistributed here)

| What | Licence |
|---|---|
| ROS 2 Kilted (`ros:kilted-ros-base`, Ubuntu 24.04), Fast DDS | Apache-2.0, BSD and others; Ubuntu's packages under their own free licences |
| vosk 0.3.45 (with Kaldi), ctranslate2 4.8.4, sentencepiece 0.2.2 | Apache-2.0, MIT, Apache-2.0 |
| their dependencies: requests, urllib3, idna, charset-normalizer, certifi, tqdm, srt, websockets, cffi, pycparser | Apache-2.0, MIT, BSD-3-Clause, MPL-2.0 |
| The model converter, in a throwaway container: transformers, PyTorch (CPU), `python:3.11-slim` | Apache-2.0, BSD-3-Clause, PSF and Debian's |
| Webots R2025a | Apache-2.0 |
| Docker Engine, Chrome for the checks (or Chromium) | Apache-2.0; Chromium BSD-3-Clause |

## Not free: the phone itself

The page runs in the phone's own browser (Chrome for Android) and speaks with the phone's own voices (Android's
text-to-speech, usually Google's), on Android with the maker's software. atl-phone neither ships nor needs any of it in
particular: any browser with WebSocket, Web Audio and speech synthesis will do, such as Chromium or Firefox on a free
Android build (LineageOS) with a free speech engine (RHVoice, eSpeak NG). The bridge's speech recognition and
translation never use the browser's or a company's services.
