# Medieval control skin test

This fixture is verified by browser QA after the stylesheet is synced.

Acceptance assertions:

- Every native `button` outside `.map` uses `medieval-button-frame.png` as its computed background image.
- Every visible `input`, `select`, and `textarea` outside `.map` uses `medieval-input-frame.png` as its computed background image.
- These controls have transparent CSS background color and no ordinary CSS border.
- Their text remains real DOM text/value and readable above the generated artwork.
- `draggable` is false and native dragstart is prevented for controls and decorative images.
- Existing `.request-item[draggable="true"]` remains draggable.
- The map retains its pan behavior.
