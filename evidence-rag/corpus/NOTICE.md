# Licensed corpus — attribution and provenance

Every file under `raw/` was fetched verbatim from the URL recorded in
`manifest.json` on the date recorded there, and is used under the
license of the project it belongs to. The license texts are kept in
`licenses/` and their sha256 is recorded in the manifest.

| Document | Project | License | Copyright |
|---|---|---|---|
| `fastapi-path-params.md` | FastAPI | MIT ([The MIT License (MIT)](https://github.com/tiangolo/fastapi/blob/master/LICENSE)) | Copyright (c) 2018 Sebastián Ramírez |
| `uvicorn-settings.md` | uvicorn | BSD-3-Clause ([BSD 3-Clause License](https://github.com/encode/uvicorn/blob/master/LICENSE.md)) | Copyright © 2017-present, Encode OSS Ltd |
| `uvicorn-server-behavior.md` | uvicorn | BSD-3-Clause ([BSD 3-Clause License](https://github.com/encode/uvicorn/blob/master/LICENSE.md)) | Copyright © 2017-present, Encode OSS Ltd |
| `httpx-quickstart.md` | httpx | BSD-3-Clause ([BSD 3-Clause License](https://github.com/encode/httpx/blob/master/LICENSE.md)) | Copyright © 2019, Encode OSS Ltd |
| `httpx-troubleshooting.md` | httpx | BSD-3-Clause ([BSD 3-Clause License](https://github.com/encode/httpx/blob/master/LICENSE.md)) | Copyright © 2019, Encode OSS Ltd |
| `starlette-requests.md` | Starlette | BSD-3-Clause ([BSD 3-Clause License](https://github.com/encode/starlette/blob/master/LICENSE.md)) | Copyright © 2018, Encode OSS Ltd |
| `starlette-responses.md` | Starlette | BSD-3-Clause ([BSD 3-Clause License](https://github.com/encode/starlette/blob/master/LICENSE.md)) | Copyright © 2018, Encode OSS Ltd |

The MIT and BSD 3-Clause licenses both require the above copyright
notice and this permission notice to be included in copies or
substantial portions of the software; they are retained in
`licenses/`. This folder redistributes documentation excerpts for
evaluation purposes with attribution, which both licenses permit.

Nothing else in this repository is derived from these files: the
synthetic fixture in `labeled_corpus.py` is original work.
