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
