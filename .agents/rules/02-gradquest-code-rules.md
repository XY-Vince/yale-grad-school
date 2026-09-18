# GradQuest Code Rules

Activation: Model Decision

Use when editing JavaScript, HTML, CSS, Python test/playtest scripts, or game
mechanics.

## JavaScript and Game State

- Prefer the local patterns already used in `docs/index.html`.
- Use `updateState(changes, owner)` for state mutations when practical.
- Runtime `statuses` are a `Set`; serialized `statuses` are arrays.
- New persistent fields need defaults in `initState()` and migration handling
  when older saves may exist.
- Keep `GAME_VERSION` as the only save/UI version source.
- Keep `MAX_STRESS` and UI stress labels on the same scale.

## Defense

- Defense eligibility belongs in `GRADUATION_CONTRACT`.
- `evaluateDefenseCriteria()` may compute skepticism labels and breakdowns, but
  must delegate eligibility to the contract.
- Shipped defense entry points should start the 3-turn gauntlet, not one-shot
  `attemptDefense()`.

## Conferences

- Manual conference actions and auto-invites must respect:
  - max 2 conferences per year
  - 2-month cooldown from `lastConferenceMonth`
  - one selected choice per active invite

## Event Routing

- Modal-producing messages should go through `showMessage()` and
  `EventResolver`.
- Silent/background log messages must stay non-modal.
- One modal per turn is a user-experience contract.

## Python Helpers

- Use `Path(__file__).resolve().parent` or `Path.as_uri()` for repo-relative
  paths.
- Keep shebangs on line 1 in executable scripts.
- Run `python3 -m compileall -q <changed-python-files>` after editing Python.

