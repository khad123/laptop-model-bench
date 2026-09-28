# Local App Benchmark — Copy-Ready Prompts

Use one prompt per fresh model conversation. Copy the complete prompt block for the task you are running. Do not include the heading or code fence.

Each prompt is standalone and repeats the same build rules so no model depends on earlier conversation context. The pack now covers five existing projects refined for focused, testable behavior, Pocket Courier, six practical apps, and two classic games. Every project uses fictional/local data and a self-contained HTML deliverable so results can be compared across models and between Normal and ECC modes.

## 1. Pocket Dodge

```text
SHARED BUILD RULES
- Return exactly one complete HTML document beginning with <!doctype html>. Put all CSS and JavaScript inside it. Return no Markdown fences, commentary, TODOs, placeholders, or omitted code.
- Deliver only index.html. It must work from a basic local HTTP server at http://localhost, with no build step, package installation, backend, network access, external libraries, remote assets, or remote fonts.
- Build a real usable app/game. Every visible control must work, state changes must be reflected in the interface, rules must be enforced, and actions must provide clear feedback. Do not add controls that do nothing.
- Use an original visual design with clear hierarchy, readable text, consistent spacing, and restrained color. Make it usable on desktop and narrow mobile screens. Use semantic HTML, accessible labels, visible keyboard focus, and keyboard support for the main actions.
- Include a short first-use explanation and useful empty, success, and error states where appropriate. Validate user input and handle invalid or missing saved data without crashing.
- Keep logic readable and prioritize a complete core loop over optional features. Use Canvas, CSS, HTML, or inline SVG for original visuals. Do not imitate a specific commercial product’s branding.
- If saving data, use a project-specific localStorage key that includes location.pathname. Provide a visible reset action with confirmation where reset could erase user-created data. Fresh users must be able to start immediately.

Finish the complete HTML document now. Return only the HTML.

PROJECT: POCKET DODGE — ARCADE SURVIVAL GAME
Create a quick-to-learn survival game in which the player steers a small ship through a bounded arena while hazards cross the field.

CORE REQUIREMENTS
1. Show a start screen with title, goal, controls, and a working Start button. Start begins play; pause/resume, restart, and game-over actions work.
2. Move the ship with arrow keys or WASD. Support pointer/touch steering within the arena. Keep the ship inside the play area.
3. Spawn at least two distinct hazard types with visible movement and real collision checks. Give a brief start-of-run grace period, then end the run on collision.
4. Increase difficulty gradually, track survival score and best score, and save the best score locally. Pause must stop game time and hazards.
5. Use requestAnimationFrame and scale the playfield to its container. Avoid fixed-resolution-only behavior and avoid excessive flashing.

VISUAL DIRECTION
A polished neon arcade cabinet: midnight playfield, subtle stars or grid, bright cyan player, and a small palette of geometric hazards. Keep score readable without covering play.
```

---

## 2. Switchyard

```text
SHARED BUILD RULES
- Return exactly one complete HTML document beginning with <!doctype html>. Put all CSS and JavaScript inside it. Return no Markdown fences, commentary, TODOs, placeholders, or omitted code.
- Deliver only index.html. It must work from a basic local HTTP server at http://localhost, with no build step, package installation, backend, network access, external libraries, remote assets, or remote fonts.
- Build a real usable app/game. Every visible control must work, state changes must be reflected in the interface, rules must be enforced, and actions must provide clear feedback. Do not add controls that do nothing.
- Use an original visual design with clear hierarchy, readable text, consistent spacing, and restrained color. Make it usable on desktop and narrow mobile screens. Use semantic HTML, accessible labels, visible keyboard focus, and keyboard support for the main actions.
- Include a short first-use explanation and useful empty, success, and error states where appropriate. Validate user input and handle invalid or missing saved data without crashing.
- Keep logic readable and prioritize a complete core loop over optional features. Use Canvas, CSS, HTML, or inline SVG for original visuals. Do not imitate a specific commercial product’s branding.
- If saving data, use a project-specific localStorage key that includes location.pathname. Provide a visible reset action with confirmation where reset could erase user-created data. Fresh users must be able to start immediately.

Finish the complete HTML document now. Return only the HTML.

PROJECT: SWITCHYARD — RAIL-ROUTING PUZZLE
Build a compact puzzle in which the player sets track switches and sends a train from the station to the goal. Use these three authored levels exactly; do not randomize or alter their connections:
- Level 1: S—J1; J1 East reaches G, North reaches dead end X. Correct setting: East.
- Level 2: S—J1; J1 North reaches J2, East reaches dead end X; J2 East reaches G, North reaches dead end Y. Correct settings: J1 North, J2 East.
- Level 3: S—J1; J1 East reaches J2, North reaches dead end X; J2 South reaches G, East reaches dead end Y. Correct settings: J1 East, J2 South.

CORE REQUIREMENTS
1. Draw a clear top-down board where every visible track segment matches the route logic. Show start, goal, switches, branches, and dead ends.
2. Let the player select each switch and cycle only its legal exits; display its selected direction. Run train animates along the graph using current settings. Correct route completes the level; a wrong branch stops at a dead end and reports a useful hint.
3. Provide working undo for the last switch change, reset level, move count, next-level, and replay actions. Explain controls before play.
4. Keep route-critical labels legible and board controls usable on narrow screens. Do not reveal the answer before an attempt.

VISUAL DIRECTION
An illustrated miniature railway with green terrain, warm track ties, a red locomotive, and restrained scenery. Use side panels for level, moves, switch directions, and actions.
```

---

## 3. Workshop Queue

```text
SHARED BUILD RULES
- Return exactly one complete HTML document beginning with <!doctype html>. Put all CSS and JavaScript inside it. Return no Markdown fences, commentary, TODOs, placeholders, or omitted code.
- Deliver only index.html. It must work from a basic local HTTP server at http://localhost, with no build step, package installation, backend, network access, external libraries, remote assets, or remote fonts.
- Build a real usable app/game. Every visible control must work, state changes must be reflected in the interface, rules must be enforced, and actions must provide clear feedback. Do not add controls that do nothing.
- Use an original visual design with clear hierarchy, readable text, consistent spacing, and restrained color. Make it usable on desktop and narrow mobile screens. Use semantic HTML, accessible labels, visible keyboard focus, and keyboard support for the main actions.
- Include a short first-use explanation and useful empty, success, and error states where appropriate. Validate user input and handle invalid or missing saved data without crashing.
- Keep logic readable and prioritize a complete core loop over optional features. Use Canvas, CSS, HTML, or inline SVG for original visuals. Do not imitate a specific commercial product’s branding.
- If saving data, use a project-specific localStorage key that includes location.pathname. Provide a visible reset action with confirmation where reset could erase user-created data. Fresh users must be able to start immediately.

Finish the complete HTML document now. Return only the HTML.

PROJECT: WORKSHOP QUEUE — SMALL BUSINESS REPAIR TRACKER
Create a local job tracker for a small electronics repair shop. A worker should quickly understand the queue, locate a job, update its status, and add or edit a repair record.

CORE REQUIREMENTS
1. Start with realistic sample jobs. Each record has an automatically assigned unique ID, customer, device, issue, status, date received, and optional notes.
2. Add and edit jobs. Require customer, device, issue, and status; validate inline and preserve entered values when showing errors.
3. Support Waiting, In Progress, Ready, and Completed statuses. Search customer/device/issue and filter by status; both must work together.
4. Selecting a job shows its details and working edit/delete actions. Confirm before deletion. Include helpful empty-queue and no-results states.
5. Persist records locally; show summary counts that update after every change. Provide a confirmed reset to sample data.

VISUAL DIRECTION
A calm small-business dashboard: warm neutral surfaces, charcoal text, one workshop-orange accent, restrained status colors, compact summary cards, a tidy job list, combined search/filter row, and a clear Add Job action. On mobile, use readable stacked cards and an easy-to-use editor.
```

---

## 4. Tower Defense

```text
SHARED BUILD RULES
- Return exactly one complete HTML document beginning with <!doctype html>. Put all CSS and JavaScript inside it. Return no Markdown fences, commentary, TODOs, placeholders, or omitted code.
- Deliver only index.html. It must work from a basic local HTTP server at http://localhost, with no build step, package installation, backend, network access, external libraries, remote assets, or remote fonts.
- Build a real usable app/game. Every visible control must work, state changes must be reflected in the interface, rules must be enforced, and actions must provide clear feedback. Do not add controls that do nothing.
- Use an original visual design with clear hierarchy, readable text, consistent spacing, and restrained color. Make it usable on desktop and narrow mobile screens. Use semantic HTML, accessible labels, visible keyboard focus, and keyboard support for the main actions.
- Include a short first-use explanation and useful empty, success, and error states where appropriate. Validate user input and handle invalid or missing saved data without crashing.
- Keep logic readable and prioritize a complete core loop over optional features. Use Canvas, CSS, HTML, or inline SVG for original visuals. Do not imitate a specific commercial product’s branding.
- If saving data, use a project-specific localStorage key that includes location.pathname. Provide a visible reset action with confirmation where reset could erase user-created data. Fresh users must be able to start immediately.

Finish the complete HTML document now. Return only the HTML.

PROJECT: TOWER DEFENSE — THREE-WAVE STRATEGY GAME
Build one complete, replayable tower-defense level. Enemies follow a fixed winding path toward an exit. The player places and upgrades defenses and tries to survive exactly three short waves.

CORE REQUIREMENTS
1. Draw one responsive map with distinct entry, winding path, exit, and legal build tiles. Use a board, Canvas, or SVG.
2. Implement three waves with visible progress. Enemies move along the path, have health, take damage, and cost a life if they reach the exit. Advance only after all spawned enemies are resolved.
3. Offer three tower types with distinct costs and combat behavior. Select a tower, then place it on an empty legal tile only if affordable. Reject path/occupied/invalid placements with clear feedback.
4. Defeated enemies award cash. Selecting a placed tower shows its details and enables a paid upgrade that changes its behavior. Explain insufficient-funds actions.
5. Provide start-wave, pause/resume, and restart. Show cash, lives, wave, selected tower, and clear win/loss states. Win only after wave three is cleared; lose at zero lives. Mouse and touch must work; give main actions keyboard access.

VISUAL DIRECTION
A bright miniature battlefield with green terrain, tan path, distinct towers and enemies, and visible targeting/firing. Keep the HUD and tower choices clear without obscuring the map. Use simple balanced numbers and a stable animation loop.
```

---

## 5. Fuel Stop

```text
SHARED BUILD RULES
- Return exactly one complete HTML document beginning with <!doctype html>. Put all CSS and JavaScript inside it. Return no Markdown fences, commentary, TODOs, placeholders, or omitted code.
- Deliver only index.html. It must work from a basic local HTTP server at http://localhost, with no build step, package installation, backend, network access, external libraries, remote assets, or remote fonts.
- Build a real usable app/game. Every visible control must work, state changes must be reflected in the interface, rules must be enforced, and actions must provide clear feedback. Do not add controls that do nothing.
- Use an original visual design with clear hierarchy, readable text, consistent spacing, and restrained color. Make it usable on desktop and narrow mobile screens. Use semantic HTML, accessible labels, visible keyboard focus, and keyboard support for the main actions.
- Include a short first-use explanation and useful empty, success, and error states where appropriate. Validate user input and handle invalid or missing saved data without crashing.
- Keep logic readable and prioritize a complete core loop over optional features. Use Canvas, CSS, HTML, or inline SVG for original visuals. Do not imitate a specific commercial product’s branding.
- If saving data, use a project-specific localStorage key that includes location.pathname. Provide a visible reset action with confirmation where reset could erase user-created data. Fresh users must be able to start immediately.

Finish the complete HTML document now. Return only the HTML.

PROJECT: FUEL STOP — TURN-BASED SHIFT MANAGEMENT GAME
Create a compact gas-station shift game. Customers arrive in a fixed queue; the player chooses a compatible pump, serves orders, and restocks fuel while trying to meet a shift target. Use turn-based pressure, never a real-time timer.

FIXED STARTING DATA
Cash $100. Regular stock 50 L at $2.50/L. Diesel stock 35 L at $3.00/L. Restock only in 25 L lots: Regular costs $40; Diesel costs $50. Fixed order sequence: Regular 20 L; Diesel 15 L; Regular 25 L; Diesel 20 L; Regular 15 L; Diesel 10 L; Regular 20 L; Diesel 15 L.

CORE REQUIREMENTS
1. Show three pumps, shop, vehicles, active customer, upcoming queue, inventory, cash, served count, and goal: serve at least 6 of 8 and finish with at least $250.
2. Select the active customer and a compatible pump, then serve with one action. Correctly update stock, cash, queue, and counts. Reject mismatched pumps, insufficient stock, and invalid actions with clear explanations.
3. Restock either fuel for the fixed cost and quantity. The active customer starts with three patience turns. Serving completes the turn; any other valid action consumes one patience turn. They leave after the third non-service turn, and the next order becomes active.
4. End with a clear win/loss summary after all orders resolve. Restart resets the fixed state and order sequence. Never add real-time countdowns.

VISUAL DIRECTION
A warm illustrated station with red-and-cream canopy, readable pumps, small cars, and a compact shop. Keep the management panels uncluttered and mobile-friendly.
```

---

## 6. Pocket Courier

```text
Build a complete, polished, playable browser game called **Pocket Courier: City Shift**.

## Deliverable and technology

Return exactly one complete HTML document beginning with `<!doctype html>`. Put all CSS and JavaScript inside it. Do not use Markdown fences, explanations, TODOs, placeholders, or omitted code.

Use plain HTML, CSS, and vanilla JavaScript. Build the city as an accessible CSS Grid of real buttons or equivalent semantic controls. Do not use a separate game engine, framework, external library, package install, remote asset, remote font, network request, or build step.

The game must run from a basic local HTTP server at `http://localhost`. Keep the code readable and organized. Write each style rule and function once; avoid repeated code. Before returning the document, check that the HTML is complete, referenced elements exist, and every visible control has working behavior.

## Game concept

The player is a bicycle courier completing three short delivery shifts in a small city. Each shift is a turn-based route puzzle: move between legal street tiles, deliver three packages in a required order, and return to the courier hub before running out of moves.

Make the game understandable immediately, with a clear start screen, short instructions, visible orders, current location, move count, and shift status. There is no real-time timer.

## Fixed city map

Use the same 7-column by 7-row city grid in all three shifts. Coordinates start at `(0,0)` in the upper-left; `x` increases to the right and `y` increases downward.

- Courier hub: `(0,0)`
- Café: `(6,0)`, named **A**
- Clinic: `(6,6)`, named **B**
- Home: `(0,6)`, named **C**
- Blocked street tiles: `(2,0)`, `(2,1)`, `(2,2)`, `(2,3)`, `(4,3)`, `(4,5)`, `(1,5)`, `(2,5)`, `(3,5)`
- Every other tile is a street.

Keep these coordinates and connections unchanged. The map is connected and has legal routes between every location.

## Three fixed shifts

Display the required delivery order and move limit for the current shift:

1. **Morning:** Café A → Clinic B → Home C → return to Hub. Move limit: **35**. Minimum route length: **32** moves.
2. **Afternoon:** Home C → Café A → Clinic B → return to Hub. Move limit: **40**. Minimum route length: **36** moves.
3. **Evening:** Clinic B → Home C → Café A → return to Hub. Move limit: **48**. Minimum route length: **44** moves.

A package is delivered only when the courier reaches the next required stop. Reaching a later stop too early does not deliver that package. After all three deliveries, the courier must return to the hub to complete the shift.

## Gameplay and controls

- Show a start screen with the game title, objective, controls, and a working **Start Shift** button.
- Allow movement by arrow keys or WASD. Also provide visible directional buttons for mouse and touch users.
- A valid move travels exactly one street tile horizontally or vertically and uses one move. No diagonal movement.
- Reject movement into a blocked tile or outside the map. Explain the invalid move and do not spend a move.
- Show the courier’s position, all delivery locations, blocked streets, active destination, completed stops, moves used, and moves remaining.
- Give clear feedback when a package is delivered, when the courier reaches the hub too early, and when the shift is completed or failed.
- If the move limit is reached before completing the shift, show a clear failure state with working **Retry Shift** and **Restart Game** actions.
- After a successful shift, show a summary and a working **Next Shift** action. After Shift 3, show a completion screen with a working replay option.

## Helpful route and recovery actions

- Add a working **Show Next Route** control. Use breadth-first search or another correct shortest-path method to highlight a legal shortest path from the courier’s current tile to the next required destination (or the hub after the deliveries). The route preview must not move the courier or deliver packages.
- Add a working **Undo Move** action. It restores the exact previous position, delivery progress, and move count.
- Add a working **Reset Shift** action with a confirmation before discarding the current shift’s progress.

## Progress and state

- Persist completed shifts and best move count per shift in `localStorage`.
- Namespace the storage key with a Pocket Courier prefix and `location.pathname` so separate model folders do not share saved progress.
- Load saved data safely. If stored data is missing or invalid, start with fresh progress without crashing.
- Provide a visible **Reset Saved Progress** action with confirmation.
- Ensure a fresh user can start immediately, and that saved progress does not prevent replaying a shift.

## Visual and accessibility requirements

Create a polished miniature-city game interface: a colorful top-down street grid, distinct buildings for the hub, café, clinic, and home, clear roadblocks, and a visible courier marker. Use a concise HUD or side panel for the active order, delivery checklist, shift, and move budget.

Use a responsive layout that remains usable on a narrow screen. Keep essential controls visible, use readable contrast and visible keyboard focus, and give map tiles and controls useful accessible labels. Use CSS shapes, text, or inline SVG only; no downloaded art.

## Final quality bar

Prioritize a complete, playable game loop over extra features. Make sure the shift rules match the fixed data above, the route preview respects blocked streets, undo restores state correctly, saved progress works, and restart/retry/next-shift controls work. Do not add controls that look interactive but do nothing.
```

---

## 7. Soundboard Studio

```text
SHARED BUILD RULES
- Return exactly one complete HTML document beginning with <!doctype html>. Put all CSS and JavaScript inside it. Return no Markdown fences, commentary, TODOs, placeholders, or omitted code.
- Deliver only index.html. It must work from a basic local HTTP server at http://localhost, with no build step, package installation, backend, network access, external libraries, remote assets, or remote fonts.
- Build a real usable app/game. Every visible control must work, state changes must be reflected in the interface, rules must be enforced, and actions must provide clear feedback. Do not add controls that do nothing.
- Use an original visual design with clear hierarchy, readable text, consistent spacing, and restrained color. Make it usable on desktop and narrow mobile screens. Use semantic HTML, accessible labels, visible keyboard focus, and keyboard support for the main actions.
- Include a short first-use explanation and useful empty, success, and error states where appropriate. Validate user input and handle invalid or missing saved data without crashing.
- Keep logic readable and prioritize a complete core loop over optional features. Use Canvas, CSS, HTML, or inline SVG for original visuals. Do not imitate a specific commercial product’s branding.
- If saving data, use a project-specific localStorage key that includes location.pathname. Provide a visible reset action with confirmation where reset could erase user-created data. Fresh users must be able to start immediately.

Finish the complete HTML document now. Return only the HTML.

PROJECT: SOUNDBOARD STUDIO — INTERACTIVE AUDIO APP
Create a small, polished soundboard for triggering and organizing a set of original synthesized sounds. No audio files or network access are allowed; use the Web Audio API after a user gesture.

CORE REQUIREMENTS
1. Provide 8 clearly named sound pads grouped into at least two categories. Each pad produces a distinct short synthesized tone or noise and visibly responds while playing.
2. Include working master volume, mute, stop-all, and category filtering. Prevent overlapping clicks from creating uncontrolled audio; make each sound short and safe at a comfortable default volume.
3. Support keyboard shortcuts for pads and pointer/touch activation. Show each shortcut in the UI and provide accessible labels/focus states.
4. Let the user rename a pad and change its assigned shortcut; validate duplicate/invalid shortcuts with a helpful message. Persist these settings locally and provide a confirmed reset to defaults.
5. Handle browsers where audio cannot start until a gesture: show a simple enable-audio instruction and recover without an error.

VISUAL DIRECTION
A responsive studio console with a distinctive pad grid, subtle waveform/level accents, clear active states, and a compact control strip. Make it feel like a useful lightweight tool, not a game.
```

---

## 8. Budget Tracker

```text
SHARED BUILD RULES
- Return exactly one complete HTML document beginning with <!doctype html>. Put all CSS and JavaScript inside it. Return no Markdown fences, commentary, TODOs, placeholders, or omitted code.
- Deliver only index.html. It must work from a basic local HTTP server at http://localhost, with no build step, package installation, backend, network access, external libraries, remote assets, or remote fonts.
- Build a real usable app/game. Every visible control must work, state changes must be reflected in the interface, rules must be enforced, and actions must provide clear feedback. Do not add controls that do nothing.
- Use an original visual design with clear hierarchy, readable text, consistent spacing, and restrained color. Make it usable on desktop and narrow mobile screens. Use semantic HTML, accessible labels, visible keyboard focus, and keyboard support for the main actions.
- Include a short first-use explanation and useful empty, success, and error states where appropriate. Validate user input and handle invalid or missing saved data without crashing.
- Keep logic readable and prioritize a complete core loop over optional features. Use Canvas, CSS, HTML, or inline SVG for original visuals. Do not imitate a specific commercial product’s branding.
- If saving data, use a project-specific localStorage key that includes location.pathname. Provide a visible reset action with confirmation where reset could erase user-created data. Fresh users must be able to start immediately.

Finish the complete HTML document now. Return only the HTML.

PROJECT: BUDGET TRACKER — PERSONAL FINANCE APP
Build a small local-first monthly budget tracker using fictional sample data. This is a planning tool, not a banking connection or financial advice service.

CORE REQUIREMENTS
1. Seed a useful sample month with income and expense transactions. Each transaction has description, amount, type, category, and date.
2. Add, edit, and delete transactions with validation: non-empty description/category, positive finite amount, valid date, and income/expense type. Confirm destructive deletion.
3. Show total income, total expenses, and remaining balance for the selected month. Filter by category/type and search description; filters must compose correctly.
4. Allow switching months and show a helpful empty-month state. Show a simple category spending breakdown with accessible labels; do not rely on color alone.
5. Persist changes locally and provide a confirmed reset to sample data. Make currency consistent (USD) and calculate totals from transaction data rather than hard-coded summary values.

VISUAL DIRECTION
A calm, trustworthy personal dashboard with a monthly summary, clear transaction list, one simple chart or bar breakdown, and an obvious Add Transaction action. Use clean typography and responsive stacked rows on mobile.
```

---

## 9. Kanban Board

```text
SHARED BUILD RULES
- Return exactly one complete HTML document beginning with <!doctype html>. Put all CSS and JavaScript inside it. Return no Markdown fences, commentary, TODOs, placeholders, or omitted code.
- Deliver only index.html. It must work from a basic local HTTP server at http://localhost, with no build step, package installation, backend, network access, external libraries, remote assets, or remote fonts.
- Build a real usable app/game. Every visible control must work, state changes must be reflected in the interface, rules must be enforced, and actions must provide clear feedback. Do not add controls that do nothing.
- Use an original visual design with clear hierarchy, readable text, consistent spacing, and restrained color. Make it usable on desktop and narrow mobile screens. Use semantic HTML, accessible labels, visible keyboard focus, and keyboard support for the main actions.
- Include a short first-use explanation and useful empty, success, and error states where appropriate. Validate user input and handle invalid or missing saved data without crashing.
- Keep logic readable and prioritize a complete core loop over optional features. Use Canvas, CSS, HTML, or inline SVG for original visuals. Do not imitate a specific commercial product’s branding.
- If saving data, use a project-specific localStorage key that includes location.pathname. Provide a visible reset action with confirmation where reset could erase user-created data. Fresh users must be able to start immediately.

Finish the complete HTML document now. Return only the HTML.

PROJECT: KANBAN BOARD — PERSONAL TASK APP
Create a polished, single-user board for organizing a small project. Keep it focused: To Do, In Progress, and Done columns.

CORE REQUIREMENTS
1. Start with several realistic sample cards. A card has title, optional description, priority, and status. Add, edit, and delete cards; validate the title and confirm deletion.
2. Move cards between columns with drag-and-drop and provide accessible keyboard/button alternatives such as Move Left/Move Right. Update the board immediately and accurately.
3. Search by title/description and filter by priority; both filters work at once. Show per-column counts and useful empty-column/no-results states.
4. Persist board changes locally. Include a confirmed reset to sample cards.
5. Keep interactions usable with mouse, keyboard, and touch. Avoid relying on drag-and-drop as the only way to move a card.

VISUAL DIRECTION
A clean project workspace with three distinct columns, compact cards, restrained priority badges, clear Add Task action, and a responsive horizontal or stacked mobile layout. Distinguish this productivity app from the game prompts.
```

---

## 10. Study Cards

```text
SHARED BUILD RULES
- Return exactly one complete HTML document beginning with <!doctype html>. Put all CSS and JavaScript inside it. Return no Markdown fences, commentary, TODOs, placeholders, or omitted code.
- Deliver only index.html. It must work from a basic local HTTP server at http://localhost, with no build step, package installation, backend, network access, external libraries, remote assets, or remote fonts.
- Build a real usable app/game. Every visible control must work, state changes must be reflected in the interface, rules must be enforced, and actions must provide clear feedback. Do not add controls that do nothing.
- Use an original visual design with clear hierarchy, readable text, consistent spacing, and restrained color. Make it usable on desktop and narrow mobile screens. Use semantic HTML, accessible labels, visible keyboard focus, and keyboard support for the main actions.
- Include a short first-use explanation and useful empty, success, and error states where appropriate. Validate user input and handle invalid or missing saved data without crashing.
- Keep logic readable and prioritize a complete core loop over optional features. Use Canvas, CSS, HTML, or inline SVG for original visuals. Do not imitate a specific commercial product’s branding.
- If saving data, use a project-specific localStorage key that includes location.pathname. Provide a visible reset action with confirmation where reset could erase user-created data. Fresh users must be able to start immediately.

Finish the complete HTML document now. Return only the HTML.

PROJECT: STUDY CARDS — FLASHCARD STUDY APP
Build a local flashcard app for studying a small built-in deck and creating a few custom cards.

CORE REQUIREMENTS
1. Include a starter deck of at least 8 question/answer cards. Show one card at a time; Flip reveals the answer. Previous/Next navigate without losing deck order.
2. Provide working Again and Know It actions. Track reviewed, known, and needs-review counts for the current session. A Shuffle action changes card order without duplicating or dropping cards.
3. Let the user add, edit, and delete cards with validation for non-empty front/back. Confirm deletion. Include a usable empty-deck state.
4. Persist custom cards locally and include a confirmed reset to the starter deck. Keep study-session counts understandable and avoid pretending that session-only counts persist if they do not.
5. Support keyboard navigation and visible focus. Keep text readable on mobile and long answers scrollable without breaking the layout.

VISUAL DIRECTION
A focused study desk interface with a large legible card, restrained progress indicator, clear study actions, and a compact deck editor. Avoid distracting animations.
```

---

## 11. E-commerce Store

```text
SHARED BUILD RULES
- Return exactly one complete HTML document beginning with <!doctype html>. Put all CSS and JavaScript inside it. Return no Markdown fences, commentary, TODOs, placeholders, or omitted code.
- Deliver only index.html. It must work from a basic local HTTP server at http://localhost, with no build step, package installation, backend, network access, external libraries, remote assets, or remote fonts.
- Build a real usable app/game. Every visible control must work, state changes must be reflected in the interface, rules must be enforced, and actions must provide clear feedback. Do not add controls that do nothing.
- Use an original visual design with clear hierarchy, readable text, consistent spacing, and restrained color. Make it usable on desktop and narrow mobile screens. Use semantic HTML, accessible labels, visible keyboard focus, and keyboard support for the main actions.
- Include a short first-use explanation and useful empty, success, and error states where appropriate. Validate user input and handle invalid or missing saved data without crashing.
- Keep logic readable and prioritize a complete core loop over optional features. Use Canvas, CSS, HTML, or inline SVG for original visuals. Do not imitate a specific commercial product’s branding.
- If saving data, use a project-specific localStorage key that includes location.pathname. Provide a visible reset action with confirmation where reset could erase user-created data. Fresh users must be able to start immediately.

Finish the complete HTML document now. Return only the HTML.

PROJECT: E-COMMERCE STORE — LOCAL SAMPLE SHOP
Create a polished fictional online shop that demonstrates a complete browse-to-checkout flow using local sample data. This is a front-end demo: do not connect to a real store, collect payment details, or claim to place a real order.

CORE REQUIREMENTS
1. Show at least 8 fictional products with name, category, price, short description, and stock count. Use original CSS/inline-SVG product artwork or simple shapes; no remote images.
2. Search products, filter by category, and sort by price/name. These controls must work together and show a useful no-results state.
3. Selecting a product opens a detail view with working quantity controls and Add to Cart. Enforce stock limits and explain unavailable/over-limit choices.
4. Show a cart with editable quantities, remove action, subtotal, and clear empty-cart state. Totals must be calculated from current cart contents.
5. Checkout asks only for a fictional name and delivery choice, validates them, then shows an order confirmation with itemized total and order number. It must not request card/bank data or imply a real purchase. Provide a way to start a fresh shopping session.

VISUAL DIRECTION
A modern, welcoming small-brand storefront with clear product cards, search/category controls, cart summary, and responsive layouts. Make product information and total costs easy to scan; do not imitate Amazon branding.
```

---

## 12. Movie Catalog

```text
SHARED BUILD RULES
- Return exactly one complete HTML document beginning with <!doctype html>. Put all CSS and JavaScript inside it. Return no Markdown fences, commentary, TODOs, placeholders, or omitted code.
- Deliver only index.html. It must work from a basic local HTTP server at http://localhost, with no build step, package installation, backend, network access, external libraries, remote assets, or remote fonts.
- Build a real usable app/game. Every visible control must work, state changes must be reflected in the interface, rules must be enforced, and actions must provide clear feedback. Do not add controls that do nothing.
- Use an original visual design with clear hierarchy, readable text, consistent spacing, and restrained color. Make it usable on desktop and narrow mobile screens. Use semantic HTML, accessible labels, visible keyboard focus, and keyboard support for the main actions.
- Include a short first-use explanation and useful empty, success, and error states where appropriate. Validate user input and handle invalid or missing saved data without crashing.
- Keep logic readable and prioritize a complete core loop over optional features. Use Canvas, CSS, HTML, or inline SVG for original visuals. Do not imitate a specific commercial product’s branding.
- If saving data, use a project-specific localStorage key that includes location.pathname. Provide a visible reset action with confirmation where reset could erase user-created data. Fresh users must be able to start immediately.

Finish the complete HTML document now. Return only the HTML.

PROJECT: MOVIE CATALOG — LOCAL DISCOVERY APP
Create a polished movie-discovery interface with a built-in fictional catalog. It may feel like a streaming catalog, but it must not claim to stream or play licensed films.

CORE REQUIREMENTS
1. Include at least 12 fictional titles with title, genre, year, short synopsis, runtime, and a simple rating. Use original text-based posters or CSS artwork, not remote images.
2. Search title/synopsis, filter by genre, and sort by title/year/rating. These controls compose correctly and show a no-results state.
3. Selecting a title opens a detail view with full synopsis and a working add/remove watchlist action. The watchlist has its own view/filter and persists locally.
4. Provide a “Mark as watched” action and a visible watched status/count. Allow undoing the watched state. Do not include a fake play button or pretend video playback works.
5. Provide a confirmed reset for locally saved watchlist/watched data. Use accessible labels and keyboard operation for search, cards, and detail actions.

VISUAL DIRECTION
A cinematic but original dark catalog with strong poster-like CSS artwork, readable metadata, and a responsive browse/watchlist layout. Do not copy Netflix logos, names, or branded interface details.
```

---

## 13. Sudoku

```text
SHARED BUILD RULES
- Return exactly one complete HTML document beginning with <!doctype html>. Put all CSS and JavaScript inside it. Return no Markdown fences, commentary, TODOs, placeholders, or omitted code.
- Deliver only index.html. It must work from a basic local HTTP server at http://localhost, with no build step, package installation, backend, network access, external libraries, remote assets, or remote fonts.
- Build a real usable app/game. Every visible control must work, state changes must be reflected in the interface, rules must be enforced, and actions must provide clear feedback. Do not add controls that do nothing.
- Use an original visual design with clear hierarchy, readable text, consistent spacing, and restrained color. Make it usable on desktop and narrow mobile screens. Use semantic HTML, accessible labels, visible keyboard focus, and keyboard support for the main actions.
- Include a short first-use explanation and useful empty, success, and error states where appropriate. Validate user input and handle invalid or missing saved data without crashing.
- Keep logic readable and prioritize a complete core loop over optional features. Use Canvas, CSS, HTML, or inline SVG for original visuals. Do not imitate a specific commercial product’s branding.
- If saving data, use a project-specific localStorage key that includes location.pathname. Provide a visible reset action with confirmation where reset could erase user-created data. Fresh users must be able to start immediately.

Finish the complete HTML document now. Return only the HTML.

PROJECT: SUDOKU — SINGLE-PLAYER NUMBER PUZZLE
Build a complete 9×9 Sudoku game using this fixed puzzle and solution so every run is deterministic and verifiable. A zero represents an empty cell.

Puzzle rows:
530070000
600195000
098000060
800060003
400803001
700020006
060000280
000419005
000080079

Solution rows:
534678912
672195348
198342567
859761423
426853791
713924856
961537284
287419635
345286179

CORE REQUIREMENTS
1. Render a clear 9×9 board with 3×3 box boundaries, fixed clues, selected cell, and related row/column/box highlights. Never allow editing a clue.
2. Select cells by pointer/touch or keyboard. Enter digits 1–9 with keyboard and an on-screen keypad; support erase. Highlight conflicts without changing fixed clues.
3. Include Check Board feedback, mistake count, and a completion state only when all cells match a valid solution. Do not mark an incomplete board solved.
4. Provide working notes mode (notes toggle per editable cell), undo for the last entry/erase, reset puzzle, and a new-game/replay action. Reset returns to the same fixed puzzle and clears user entries after confirmation.
5. Make the board accessible with useful cell labels and keyboard navigation; keep controls usable on narrow mobile screens.

VISUAL DIRECTION
A calm, elegant number-puzzle interface with a highly legible grid, restrained selected/conflict colors, and a compact keypad/action row. Avoid game art that makes the digits harder to read.
```

---

## 14. Tic-Tac-Toe

```text
SHARED BUILD RULES
- Return exactly one complete HTML document beginning with <!doctype html>. Put all CSS and JavaScript inside it. Return no Markdown fences, commentary, TODOs, placeholders, or omitted code.
- Deliver only index.html. It must work from a basic local HTTP server at http://localhost, with no build step, package installation, backend, network access, external libraries, remote assets, or remote fonts.
- Build a real usable app/game. Every visible control must work, state changes must be reflected in the interface, rules must be enforced, and actions must provide clear feedback. Do not add controls that do nothing.
- Use an original visual design with clear hierarchy, readable text, consistent spacing, and restrained color. Make it usable on desktop and narrow mobile screens. Use semantic HTML, accessible labels, visible keyboard focus, and keyboard support for the main actions.
- Include a short first-use explanation and useful empty, success, and error states where appropriate. Validate user input and handle invalid or missing saved data without crashing.
- Keep logic readable and prioritize a complete core loop over optional features. Use Canvas, CSS, HTML, or inline SVG for original visuals. Do not imitate a specific commercial product’s branding.
- If saving data, use a project-specific localStorage key that includes location.pathname. Provide a visible reset action with confirmation where reset could erase user-created data. Fresh users must be able to start immediately.

Finish the complete HTML document now. Return only the HTML.

PROJECT: TIC-TAC-TOE — TWO-PLAYER GAME
Create a polished local two-player Tic-Tac-Toe game. Keep turns on the same device; no online play or computer opponent is required.

CORE REQUIREMENTS
1. Show a 3×3 board and clearly indicate whose turn it is. Players alternate X and O only in empty cells.
2. Detect all eight winning lines and draws. A win highlights the exact three cells, updates the correct score, and prevents additional moves until a new round starts.
3. Provide working New Round and Reset Scores actions. Reset Scores requires confirmation; New Round clears the board but preserves scores and alternates who starts next.
4. Show clear status before, during, and after play. Never overwrite an occupied cell or increment scores more than once for one result.
5. Support keyboard/pointer/touch input, accessible cell labels, visible focus, and a responsive board.

VISUAL DIRECTION
A crisp, friendly tabletop style with distinct X/O marks, smooth but restrained placement feedback, clear scorekeeping, and no clutter. Make the board the visual focus.
```
