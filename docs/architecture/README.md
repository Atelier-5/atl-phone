# The phone bridge's architecture pack

Open `index.html` (or `/docs/` on a running bridge): the thirteen diagrams, what each one answers, and the review findings.

| | Diagram | Type |
|---|---|---|
| 01 | From `./start.sh` to a tested phone | workflow |
| 02 | What the bridge keeps in memory | data model (ERD) |
| 03 | One setup test, there and back | sequence |
| 04 | The phone's link to the bridge | lifecycle |
| 05 | A second phone takes over (race) | sequence |
| 06 | The Desk Guardian's states | lifecycle |
| 07 | The guardian sees a face, then its owner | sequence |
| 08 | What flows between the phone and ROS 2 | data flow |
| 09 | The real phone and its Webots twin, wired to the bridge | architecture |
| 10 | A tap on the phone, drawn by its Webots twin | sequence |
| 11 | The lab, now: everything on the PC, the phone on its USB | architecture |
| 12 | Autonomous (designed): the Pi on the robot runs the brain | architecture |
| 13 | Recognition: the phone sees, the Pi decides on numbers | architecture |

- `src/*.json`: the Archify sources. Each box cites repository lines at the commit in `meta.repository`.
- `*.html`: the rendered diagrams, standalone (open them from disk). `*.delivery.json`: their provenance.
- `receipts/`: each run's validation and real-browser check, and `summary.json`.

Rebuild with `python3 build.py` (or `python3 build.py 03- 05-` for some). It needs Node.js 18+ and the Archify skill
(`~/.agents/skills/archify` or `~/.claude/skills/archify`). Archify checks every citation against the commit's bytes and
wants the repository's origin to match `meta.repository.url`. While this repository has no origin yet, `build.py` runs
the check on a throwaway clone that carries the intended origin, and leaves this repository's configuration alone.

After a code change: update the cited lines and `meta.repository.revision` in `src/`, commit the code first, then rebuild.

License: GPL-3.0-or-later.
