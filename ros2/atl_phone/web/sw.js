// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Atelier-5
// The face's service worker: it only makes the face installable as its own app window. It keeps nothing: every page
// still comes from the bridge, so an update shows at once, and without the bridge the face says it has no link.
'use strict';
self.addEventListener('install', function () { self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', function () {});  // the network, as always
