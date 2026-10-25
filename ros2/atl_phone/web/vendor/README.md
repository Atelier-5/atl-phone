# Third-party code

- `qrcode.js`: QR Code Generator for JavaScript 1.4.4, Copyright (c) 2009 Kazuhiko Arase, MIT license
  (notice in the file's header). From the npm package `qrcode-generator`, unchanged.
  "QR Code" is a registered trademark of DENSO WAVE INCORPORATED.

- `face-api/face-api.js`: Face-API 1.7.15, Copyright (c) Vladimir Mandic, MIT license (`face-api/LICENSE`).
  From the npm package `@vladmandic/face-api` (`dist/face-api.js`), unchanged. It bundles TensorFlow.js 4.22.0,
  Copyright Google LLC, Apache License 2.0 (`face-api/LICENSE-tfjs`, from github.com/tensorflow/tfjs at tfjs-v4.22.0).
- `face-api/models/`: three of the package's pretrained models, unchanged: `tiny_face_detector` (finds faces),
  `face_landmark_68_tiny` (lines a face up) and `face_recognition` (a 128-number signature, used only for the opt-in
  "familiar" mode, in the phone's memory). The package ships them under its MIT license; they come from
  github.com/justadudewhohacks/face-api.js-models (MIT), the recognition net a port of dlib's ResNet model.

- `mediapipe/vision_bundle.mjs` and `mediapipe/wasm/vision_wasm_internal.{js,wasm}`: MediaPipe Tasks Vision 0.10.14,
  Copyright The MediaPipe Authors (Google LLC), Apache License 2.0 (`mediapipe/LICENSE`, from
  github.com/google-ai-edge/mediapipe at v0.10.14). From the npm package `@mediapipe/tasks-vision`, unchanged; only the
  SIMD build of the WebAssembly is kept (a phone without SIMD falls back to face-api for faces).
- `mediapipe/models/`: MediaPipe's published models, unchanged, Apache License 2.0 (their model cards), from
  storage.googleapis.com/mediapipe-models: `blaze_face_short_range.tflite` (finds faces), `efficientdet_lite0.tflite`
  (int8; finds the 80 kinds of COCO objects), `gesture_recognizer.task` (hands and seven gestures).
- `aruco/`: js-aruco2 2.0.0, Copyright (c) 2020 Damiano Falcioni, Copyright (c) 2011 Juan Mellado, MIT license
  (`aruco/LICENSE`): `cv.js`, `svd.js`, `posit1.js`, `aruco.js` and the dictionary `aruco_4x4_1000.js`, whose codes come
  from OpenCV (3-clause BSD license, in the file's header). From the npm package `js-aruco2`, unchanged.

- `tesseract/`: Tesseract.js 5.1.1, Copyright (c) 2016 Kevin Kwok and the Tesseract.js contributors, Apache License 2.0
  (`tesseract/LICENSE`): `tesseract.min.js` and `worker.min.js` from the npm package `tesseract.js` (`dist/`), unchanged;
  its core `tesseract-core-simd-lstm.wasm.js` and `tesseract-core-lstm.wasm.js` (Tesseract OCR compiled to WebAssembly,
  Apache License 2.0, `tesseract/LICENSE-core`) from the npm package `tesseract.js-core` 5.1.1, unchanged. Omi Assist's
  reader: the text is found and read aloud on the phone.
- `tesseract/lang/`: the German, English and French models `deu`, `eng`, `fra` (`4.0.0_best_int`) from the npm packages
  `@tesseract.js-data/<lang>` 1.0.0, unchanged; they are Tesseract's own trained data (github.com/tesseract-ocr/tessdata_best,
  Apache License 2.0).
