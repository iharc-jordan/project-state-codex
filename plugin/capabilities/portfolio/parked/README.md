# parked — designed on 2026-09-21, not shipped

Material from the first draft of the capability, before the 2026-09-22 rescope to
*understand · query · synthesize*. It is kept because the design work is real and will be
wanted; it is not in the plugin payload because it is premature. Re-design each piece against
six months of real snapshots and the questions people actually asked — the questions are what
the measures should encode.

| Directory | What it holds | Where it would go back |
|---|---|---|
| `measures/` | the four declared measure sets — health, performance, innovation, portco | `capabilities/portfolio/measures/` + payload `measures:` |
| `cards/` | battle-card templates: member, external, hopper, portfolio, exec summary, exec set | `templates/cards/` |
| `views/` | board, calendar, scorecard, exec, capacity, trajectory `dash.yaml` definitions | `views/` |

Also parked in the spec (§11), with no files: the dispatch mechanism, the fifteen-rule finding
catalogue, stances and declared investment fields, the monthly review and quarterly health
cadences, and portfolio-level harvesting with marker routing. Fixture examples of the parked
artifacts remain under `../examples/` (cards, exec, findings PF-F-004…009, brief, review) and
the rendered pages `../examples/html/portfolio-battle-cards.html` and `portfolio-exec-views.html`.
