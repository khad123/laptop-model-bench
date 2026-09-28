# Local App Benchmark — Copy-Ready Prompts

Use one prompt per fresh model conversation. Copy the complete prompt block for the task you are running. Do not include the heading or code fence.

Each prompt is standalone and repeats the same build rules so no model depends on earlier conversation context. The six tasks include arcade, puzzle, productivity, defense, management, and courier route-planning projects. The concept board is visual inspiration only; the model should create its own design.

---

## 1. Pocket Dodge

```text
You are building a complete, polished, playable browser game called Pocket Dodge.

SHARED BUILD RULES
- Return exactly one complete HTML document, beginning with <!doctype html>. Put all CSS and JavaScript inside it. Do not use Markdown fences, explanations, TODOs, placeholders, or omitted code.
- The only deliverable is index.html. It must work by opening it from a basic local HTTP server at http://localhost. Do not require a build step, package installation, separate backend, network access, external libraries, remote assets, or remote fonts.
- Implement real behavior, not a picture of an app: controls must change state, rules must be enforced, and users must receive clear feedback. Do not show controls that do nothing.
- Make an original, attractive interface with a clear visual hierarchy, consistent spacing and color, readable text, and thoughtful details. It must fit a normal desktop and a narrow mobile screen without hiding essential controls. Use visible keyboard focus and accessible labels.
- Include a brief first-use explanation, a clear title, useful current status, and the relevant working actions for this project. Support keyboard and pointer/touch input where appropriate; use visible keyboard focus and accessible labels.
- Use only original CSS, Canvas, inline SVG, or simple HTML shapes. Keep logic readable and organized. Handle invalid states safely and avoid runtime errors.
- If you save data in localStorage, use a key that includes a project-specific prefix and location.pathname so separate model/project folders do not collide. Include a visible reset action when appropriate. A fresh user must be able to start immediately.
- Prefer a small, finished experience with strong presentation over many unfinished features. Ensure the HTML is self-contained and complete before you stop.

PROJECT: POCKET DODGE
Create a quick-to-understand arcade survival game. The player controls a small ship/orb in a bounded arena and dodges falling or moving hazards for as long as possible.

FUNCTIONAL REQUIREMENTS
1. Show a polished start screen with the title, one-sentence goal, and controls. Starting begins the game loop.
2. Move the player with arrow keys or WASD. Also support pointer/touch movement by moving toward the user's pointer/finger within the arena.
3. Spawn several visually distinct hazards over time. They move through the arena and use real collision detection with the player. Give the player a brief grace period at the start so play does not end unfairly.
4. Increase challenge gradually by adjusting hazard frequency or speed. Award survival score over time and show the best score. Save the best score locally.
5. Space and a visible button toggle pause/resume. A collision ends the run, clearly shows the final score, and offers a working restart.
6. Keep motion smooth with requestAnimationFrame, scale the arena to its container, and avoid making the game depend on a fixed desktop resolution.

VISUAL DIRECTION
Create a distinctive neon arcade cabinet feel: deep midnight-blue playfield, subtle grid/stars, a bright cyan player, and a restrained palette of colorful geometric hazards. The score and best score should be obvious but not cover play. Use clean start, pause, and game-over overlays. Make the game feel lively without excessive flashing.

Finish the complete HTML document now. Return only the HTML.
```

---
## 2. Switchyard

```text
You are building a complete, polished, playable browser puzzle game called Switchyard.

SHARED BUILD RULES
- Return exactly one complete HTML document, beginning with <!doctype html>. Put all CSS and JavaScript inside it. Do not use Markdown fences, explanations, TODOs, placeholders, or omitted code.
- The only deliverable is index.html. It must work by opening it from a basic local HTTP server at http://localhost. Do not require a build step, package installation, separate backend, network access, external libraries, remote assets, or remote fonts.
- Implement real behavior, not a picture of an app: controls must change state, rules must be enforced, and users must receive clear feedback. Do not show controls that do nothing.
- Make an original, attractive interface with a clear visual hierarchy, consistent spacing and color, readable text, and thoughtful details. It must fit a normal desktop and a narrow mobile screen without hiding essential controls. Use visible keyboard focus and accessible labels.
- Include a brief first-use explanation, a clear title, useful current status, and the relevant working actions for this project. Support keyboard and pointer/touch input where appropriate; use visible keyboard focus and accessible labels.
- Use only original CSS, Canvas, inline SVG, or simple HTML shapes. Keep logic readable and organized. Handle invalid states safely and avoid runtime errors.
- If you save data in localStorage, use a key that includes a project-specific prefix and location.pathname so separate model/project folders do not collide. Include a visible reset action when appropriate. A fresh user must be able to start immediately.
- Prefer a small, finished experience with strong presentation over many unfinished features. Ensure the HTML is self-contained and complete before you stop.

PROJECT: SWITCHYARD
Build a compact rail-routing puzzle. The player configures track switches so a train can travel from its station to the goal. The puzzle must have real, pre-authored solutions; do not generate random boards that may be impossible.

FUNCTIONAL REQUIREMENTS
1. Implement these same three route fixtures, preserving every connection and direction. You may choose visual spacing, but do not change the graph:
   - Level 1: S—J1; from J1, East reaches G and North reaches dead end X. Correct switch: East.
   - Level 2: S—J1; from J1, North reaches J2 and East reaches dead end X; from J2, East reaches G and North reaches dead end Y. Correct switches: J1=North, J2=East.
   - Level 3: S—J1; from J1, East reaches J2 and North reaches dead end X; from J2, South reaches G and East reaches dead end Y. Correct switches: J1=East, J2=South.
2. Show a clear top-down grid/board. Clicking or tapping a switch cycles its route. Display the current switch direction and a visible selected/active state.
3. Provide a “Run train” action. Animate the train through the connected track according to the current switch settings. Correct routing reaches the goal and completes the level. Incorrect routing visibly stops at a dead end or takes a wrong branch and reports failure without crashing.
4. Provide working undo for the most recent switch change and a reset-level action. Track move count and level progress. After completing a level, provide a working next-level action; after the final level, show a completion screen and replay option.
5. Explain the controls before play. Do not reveal the answer automatically; give a concise status hint after a failed attempt.
6. Ensure every displayed track segment, switch, branch, start, and goal agrees with the underlying route logic. Keep the board understandable on a narrow screen.

VISUAL DIRECTION
Make a charming, carefully drawn miniature railway puzzle: green landscape, small trees/rocks, warm track ties, a red locomotive, a station, and a clear goal marker. Use a polished illustrated board with restrained side panels for level, moves, controls, undo, reset, and run. Keep visual decoration away from route-critical information.

Finish the complete HTML document now. Return only the HTML.
```

---

## 3. Workshop Queue

```text
You are building a complete, polished, usable browser app called Workshop Queue.

SHARED BUILD RULES
- Return exactly one complete HTML document, beginning with <!doctype html>. Put all CSS and JavaScript inside it. Do not use Markdown fences, explanations, TODOs, placeholders, or omitted code.
- The only deliverable is index.html. It must work by opening it from a basic local HTTP server at http://localhost. Do not require a build step, package installation, separate backend, network access, external libraries, remote assets, or remote fonts.
- Implement real behavior, not a picture of an app: controls must change state, rules must be enforced, and users must receive clear feedback. Do not show controls that do nothing.
- Make an original, attractive interface with a clear visual hierarchy, consistent spacing and color, readable text, and thoughtful details. It must fit a normal desktop and a narrow mobile screen without hiding essential controls. Use visible keyboard focus and accessible labels.
- Include a brief first-use explanation, a clear title, useful current status, and the relevant working actions for this project. Support keyboard and pointer/touch input where appropriate; use visible keyboard focus and accessible labels.
- Use only original CSS, Canvas, inline SVG, or simple HTML shapes. Keep logic readable and organized. Handle invalid states safely and avoid runtime errors.
- If you save data in localStorage, use a key that includes a project-specific prefix and location.pathname so separate model/project folders do not collide. Include a visible reset action when appropriate. A fresh user must be able to start immediately.
- Prefer a small, finished experience with strong presentation over many unfinished features. Ensure the HTML is self-contained and complete before you stop.

PROJECT: WORKSHOP QUEUE
Create a local repair-shop job tracker for a small electronics workshop. This is a productivity app, not a game. A shop worker should quickly see the queue, find a job, update its status, and add or edit a repair record.

FUNCTIONAL REQUIREMENTS
1. Include useful sample jobs at first launch. Each job has an ID, customer name, device/item, short issue description, status, date received, and optional notes.
2. Let the user create a job and edit an existing job. Require customer, device/item, issue, and status; validate them and show friendly inline errors. Assign unique IDs automatically.
3. Allow changing status among at least “Waiting”, “In Progress”, “Ready”, and “Completed”. Search by customer/device/issue and filter by status; search and filter must work together.
4. Selecting a job shows its details and gives working edit and delete actions. Ask for confirmation before deletion. Include useful empty-queue and no-search-results states.
5. Persist changes across refresh. Provide a visible action to reset to the original sample jobs, with confirmation so data is not erased accidentally.
6. Show clear summary counts by status. Every action should update the list, selected details, and counts without a page reload.

VISUAL DIRECTION
Design a calm, professional small-business dashboard, visually distinct from the games: warm light neutral surfaces, charcoal text, one workshop-orange accent, restrained status colors, a tidy table/list, compact summary cards, search and filter row, and an “Add job” button. On narrow screens, turn the job list into readable stacked cards and make the form/details easy to use. Avoid decorative game art and avoid an overly dense enterprise admin template.

Finish the complete HTML document now. Return only the HTML.
```

---

## 4. Tower Defense

```text
You are building a complete, polished, playable browser game called Tower Defense.

SHARED BUILD RULES
- Return exactly one complete HTML document, beginning with <!doctype html>. Put all CSS and JavaScript inside it. Do not use Markdown fences, explanations, TODOs, placeholders, or omitted code.
- The only deliverable is index.html. It must work by opening it from a basic local HTTP server at http://localhost. Do not require a build step, package installation, separate backend, network access, external libraries, remote assets, or remote fonts.
- Implement real behavior, not a picture of an app: controls must change state, rules must be enforced, and users must receive clear feedback. Do not show controls that do nothing.
- Make an original, attractive interface with a clear visual hierarchy, consistent spacing and color, readable text, and thoughtful details. It must fit a normal desktop and a narrow mobile screen without hiding essential controls. Use visible keyboard focus and accessible labels.
- Include a brief first-use explanation, a clear title, useful current status, and the relevant working actions for this project. Support keyboard and pointer/touch input where appropriate; use visible keyboard focus and accessible labels.
- Use only original CSS, Canvas, inline SVG, or simple HTML shapes. Keep logic readable and organized. Handle invalid states safely and avoid runtime errors.
- If you save data in localStorage, use a key that includes a project-specific prefix and location.pathname so separate model/project folders do not collide. Include a visible reset action when appropriate. A fresh user must be able to start immediately.
- Prefer a small, finished experience with strong presentation over many unfinished features. Ensure the HTML is self-contained and complete before you stop.

PROJECT: TOWER DEFENSE
Build one complete, replayable tower-defense level. Enemies follow a fixed winding path toward the exit. The player places and upgrades defenses, earns money for defeating enemies, and tries to survive three short waves.

FUNCTIONAL REQUIREMENTS
1. Draw one attractive map with a clearly marked entry, winding path, and exit. The path and buildable areas must be visually distinct. Use a responsive canvas or SVG/game board.
2. Implement exactly three short waves with visible wave progress. Enemies must move along the path, have health, take damage, and reduce player lives if they reach the exit. A wave advances only after all scheduled enemies are spawned and resolved.
3. Provide at least three tower types with distinct names, costs, ranges, fire rates, and/or damage. Selecting a tower then clicking/tapping a legal build tile places it only if the player can afford it. Towers visibly target and damage enemies. No tower may be placed on the path or another tower.
4. Award cash for defeated enemies. Let the player select an existing tower and upgrade it for a visible cost; upgrades must change its behavior. Explain insufficient-cash and invalid-placement actions.
5. Include start-wave, pause/resume, and restart. Show cash, lives, current wave, selected tower details, and clear win/loss states. Win after wave three is fully cleared; lose when lives reach zero.
6. Use a stable animation loop and simple balanced numbers. Make the game playable with mouse/touch; provide keyboard access for the main buttons and visible focus states.

VISUAL DIRECTION
Create a bright, readable miniature battlefield: lush green terrain, a winding tan path, small trees/flowers, distinct tower silhouettes, and colorful enemies. Show tower range or firing so the defense behavior is understandable. Put cash/lives/wave in a compact HUD and tower choices in a clear toolbar. Aim for a polished indie game screen without visual clutter.

Finish the complete HTML document now. Return only the HTML.
```

---

## 5. Fuel Stop

```text
You are building a complete, polished, playable browser management game called Fuel Stop.

SHARED BUILD RULES
- Return exactly one complete HTML document, beginning with <!doctype html>. Put all CSS and JavaScript inside it. Do not use Markdown fences, explanations, TODOs, placeholders, or omitted code.
- The only deliverable is index.html. It must work by opening it from a basic local HTTP server at http://localhost. Do not require a build step, package installation, separate backend, network access, external libraries, remote assets, or remote fonts.
- Implement real behavior, not a picture of an app: controls must change state, rules must be enforced, and users must receive clear feedback. Do not show controls that do nothing.
- Make an original, attractive interface with a clear visual hierarchy, consistent spacing and color, readable text, and thoughtful details. It must fit a normal desktop and a narrow mobile screen without hiding essential controls. Use visible keyboard focus and accessible labels.
- Include a brief first-use explanation, a clear title, useful current status, and the relevant working actions for this project. Support keyboard and pointer/touch input where appropriate; use visible keyboard focus and accessible labels.
- Use only original CSS, Canvas, inline SVG, or simple HTML shapes. Keep logic readable and organized. Handle invalid states safely and avoid runtime errors.
- If you save data in localStorage, use a key that includes a project-specific prefix and location.pathname so separate model/project folders do not collide. Include a visible reset action when appropriate. A fresh user must be able to start immediately.
- Prefer a small, finished experience with strong presentation over many unfinished features. Ensure the HTML is self-contained and complete before you stop.

PROJECT: FUEL STOP
Create a compact gas-station shift-management game. Customers arrive needing fuel. The player serves them, keeps stock available, manages a short queue, and meets the shift goal. This should be a playable game with a small set of clear actions, not a large business simulator.

FUNCTIONAL REQUIREMENTS
1. Show a small, attractive top-down or isometric station with three visible pumps, a shop/building, vehicles, and a customer queue. The selected customer and selected pump must be obvious.
2. Use this fixed starting state and economy: cash $100, Regular stock 50 L, Diesel stock 35 L, sale price $2.50/L Regular and $3.00/L Diesel. Restock only in 25 L lots, costing $40 for Regular or $50 for Diesel. Use this fixed customer order sequence: Regular 20 L; Diesel 15 L; Regular 25 L; Diesel 20 L; Regular 15 L; Diesel 10 L; Regular 20 L; Diesel 15 L. Show the active customer and upcoming queue.
3. Let the player select a waiting customer and a compatible pump, then serve the order with one clear action. Correctly subtract sold fuel from the matching inventory, add revenue to cash, update the served count, and remove the customer from the queue. Reject service when the pump/fuel/stock/customer selection is invalid, and explain why.
4. Let the player restock either fuel type by paying the fixed cost above. Restocking updates cash and stock consistently. One customer is active at a time and gets three action turns of patience. A service action completes that customer; any other action consumes one patience turn, and the customer leaves after their third non-service turn. The next order then arrives. Use turn-based pressure, not a real-time clock.
5. The visible win objective is to serve at least six of eight customers and finish with at least $250. End with a clear win/loss summary after all orders resolve. Provide a working restart. Do not add a real-time timer.
6. Include a concise first-use tutorial/instructions, visible fuel inventory, cash, served/remaining customers, and objective progress. Ensure all buttons and selections work on mouse/touch and remain usable on a narrow screen.

VISUAL DIRECTION
Create a warm, colorful miniature gas-station scene with a red-and-cream canopy, readable pumps, small cars, and a compact shop. Keep management information in clean panels: cash and fuel stock, customer queue/patience, selected order, shift objectives, and service/restock actions. Use friendly, polished game art made from inline shapes rather than external images. Keep text large enough to read and the play area uncluttered.

Finish the complete HTML document now. Return only the HTML.
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

Return only the complete HTML document.
```

---
