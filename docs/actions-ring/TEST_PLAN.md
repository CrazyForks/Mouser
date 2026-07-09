# Actions Ring — Test Plan

## Overview

Tests are organised into sections matching the work packages in the execution
plan. All automated tests go in `tests/test_actions_ring.py`. Manual test
procedures are listed in section M at the end.

---

## T-1: Sector Geometry

Unit tests for `ActionsRingController.angle_to_sector()`.

| ID | Test | Input | Expected |
|----|------|-------|----------|
| T-1.1 | Dead zone returns -1 | `dx=0, dy=0, N=6` | `-1` |
| T-1.2 | Dead zone edge (29 px) | `dx=0, dy=-29, N=6` | `-1` |
| T-1.3 | Just outside dead zone (31 px) | `dx=0, dy=-31, N=6` | `0` (12 o'clock) |
| T-1.4 | Sector 0 at 12 o'clock | `dx=0, dy=-100, N=4` | `0` |
| T-1.5 | Sector 1 at 3 o'clock | `dx=100, dy=0, N=4` | `1` |
| T-1.6 | Sector 2 at 6 o'clock | `dx=0, dy=100, N=4` | `2` |
| T-1.7 | Sector 3 at 9 o'clock | `dx=-100, dy=0, N=4` | `3` |
| T-1.8 | Boundary between sectors | `dx=100, dy=-100, N=4` | `0` or `1` (deterministic) |
| T-1.9 | 6-sector layout, all sectors | Angles at 0, 60, 120, 180, 240, 300 deg | `0..5` in order |
| T-1.10 | 8-sector layout | All 8 cardinal + ordinal directions | `0..7` correctly |
| T-1.11 | Minimum sectors (2) | `dx=0, dy=-100, N=2` and `dx=0, dy=100, N=2` | `0` and `1` |

---

## T-2: Controller State Machine

Unit tests for `ActionsRingController` lifecycle. Uses mock callbacks.

| ID | Test | Scenario | Expected |
|----|------|----------|----------|
| T-2.1 | Initial state is IDLE | Create controller | `state == IDLE` |
| T-2.2 | Quick press fires action | `on_button_down()`, wait 50ms, `on_button_up()` | `execute_cb` called with quick_action; state back to IDLE |
| T-2.3 | Hold triggers ring | `on_button_down()`, wait 300ms | `show_ring_cb` called; `play_haptic_cb(0)` called; `state == ACTIVE` |
| T-2.4 | Release in dead zone cancels | After hold, `on_button_up()` with cursor at center | `hide_ring_cb` called; no `execute_cb`; state back to IDLE |
| T-2.5 | Release on sector executes | After hold, cursor at sector 2, `on_button_up()` | `execute_cb` called with `slots[2]`; `play_haptic_cb(7)` called |
| T-2.6 | Double press resets cleanly | Quick press, then another quick press | Both fire quick_action; no lingering timer |
| T-2.7 | Hold then quick press | Hold (ring shows), release, then quick press | First: ring action. Second: quick action. |
| T-2.8 | Shutdown cancels timer | `on_button_down()`, immediately `shutdown()` | No callbacks fire after shutdown |
| T-2.9 | Button up before down is no-op | `on_button_up()` while IDLE | No crash, no callbacks |
| T-2.10 | Concurrent down/up doesn't race | Rapid down/up from hook thread | Lock prevents torn state |

---

## T-3: Controller Threading

Stress tests for thread safety.

| ID | Test | Scenario | Expected |
|----|------|----------|----------|
| T-3.1 | Rapid toggle stress | 100 quick down/up cycles from two threads | No deadlocks, no crashes |
| T-3.2 | Timer vs button_up race | `on_button_down()`, then `on_button_up()` at exactly 250ms | Either quick-press or ring — never both |
| T-3.3 | Shutdown during ACTIVE | Hold → ring shows → `shutdown()` from different thread | `hide_ring_cb` called, state = IDLE |

---

## T-4: Config Migration

Tests in `tests/test_config.py` (additions to existing file).

| ID | Test | Scenario | Expected |
|----|------|----------|----------|
| T-4.1 | Fresh config is v18 | Load DEFAULT_CONFIG | `version == 18`, has `actions_ring_mode`, `actions_ring_hold_ms`, `actions_ring_slots` |
| T-4.2 | v17 migrates to v18 | Config at v17 without new keys | After migration: v18, all new settings present with defaults |
| T-4.3 | Existing v17 profiles get slots | Two profiles at v17 | Both gain `actions_ring_slots` default list |
| T-4.4 | Custom actions_ring preserved | Profile with `actions_ring: "play_pause"` at v17 | `actions_ring` unchanged; `actions_ring_slots` added alongside |
| T-4.5 | v18 not double-migrated | Config already at v18 | No changes, version stays 18 |
| T-4.6 | Slots default is list of 4 | Fresh migration | `actions_ring_slots` has exactly 4 entries |

---

## T-5: Overlay Rendering

Automated tests for `ActionsRingOverlay` (requires QApplication).

| ID | Test | Scenario | Expected |
|----|------|----------|----------|
| T-5.1 | Show and hide cycle | `show_ring()` then `hide_ring()` | Widget visible then hidden, no crash |
| T-5.2 | Window flags correct | After `show_ring()` | Has `FramelessWindowHint`, `WindowStaysOnTopHint`, `Tool` |
| T-5.3 | Widget attributes | After construction | `WA_TranslucentBackground` set |
| T-5.4 | Sector highlight update | `set_highlighted_sector(2)` | `current_sector` returns 2 |
| T-5.5 | Highlight -1 clears | `set_highlighted_sector(-1)` | No highlighted sector |
| T-5.6 | Slot labels passed through | `show_ring(0, 0, ["A", "B", "C", "D"])` | Internal state has 4 labels |
| T-5.7 | Paint doesn't crash | Call `repaint()` with 4 sectors | No exception |
| T-5.8 | Paint doesn't crash (8 sectors) | Call `repaint()` with 8 sectors | No exception |

---

## T-6: Engine Integration

Tests extending `tests/test_engine.py`.

| ID | Test | Scenario | Expected |
|----|------|----------|----------|
| T-6.1 | Ring mode creates controller | Config has `actions_ring_mode: "ring"` | Engine has `_ring` attribute |
| T-6.2 | Simple mode uses _make_handler | Config has `actions_ring_mode: "simple"` | No controller; handler registered normally |
| T-6.3 | Disabled mode skips registration | Config has `actions_ring_mode: "disabled"` | No handler for actions_ring events |
| T-6.4 | Reload config recreates controller | Change slots in config, call `reload_config()` | Controller has new slots |
| T-6.5 | Profile switch updates slots | Switch to profile with different ring slots | Controller reloaded with new slots |

---

## T-7: Backend Integration

Tests extending `tests/test_backend.py`.

| ID | Test | Scenario | Expected |
|----|------|----------|----------|
| T-7.1 | actionsRingMode readable | Backend with engine | Returns string from config |
| T-7.2 | setActionsRingMode persists | Set mode to "simple" | Config saved, settingsChanged emitted |
| T-7.3 | actionsRingSlots readable | Backend with config having slots | Returns list |
| T-7.4 | setActionsRingSlots persists | Set new slot list | Config saved, mappingsChanged emitted |
| T-7.5 | Show ring signal fires | Engine calls show callback | `_showRingRequest` signal emitted |
| T-7.6 | Hide ring signal fires | Engine calls hide callback | `_hideRingRequest` signal emitted |

---

## M: Manual Test Procedures

### M-1: Basic Ring Interaction

**Prerequisites:** MX Master 4 connected, Mouser running, actions_ring_mode = "ring"

1. **Quick press test:**
   - Press and release the thumb button quickly (< 250 ms)
   - Expected: the quick-press action fires (default: none)
   - Set quick-press to "Show Desktop", repeat
   - Expected: desktop shows/hides

2. **Hold and select test:**
   - Press and hold the thumb button for > 250 ms
   - Expected: radial overlay appears at cursor position
   - Move cursor to "Screenshot" sector
   - Expected: sector highlights with accent color
   - Release
   - Expected: screenshot is taken, overlay disappears

3. **Cancel test:**
   - Hold to show ring
   - Move cursor back to center (dead zone)
   - Release
   - Expected: no action fired, overlay disappears

4. **Haptic test:**
   - Hold thumb button
   - Expected: feel haptic pulse when ring appears (waveform 0)
   - Move to a sector and release
   - Expected: feel haptic pulse on action execution (waveform 7)

### M-2: Mode Switching

1. Switch to Simple mode in settings
   - Press thumb button → quick-press action fires immediately
   - Hold thumb button → same action fires, no ring appears

2. Switch to Disabled mode
   - Press thumb button → nothing happens

3. Switch back to Ring mode
   - Hold → ring appears as expected

### M-3: Configuration UI

1. Open Mouser, select the Actions Ring button hotspot
2. Verify mode selector shows Ring / Simple / Disabled
3. Change quick-press action — verify it takes effect
4. Add a slot to the ring — verify ring shows new sector
5. Remove a slot — verify ring updates
6. Change hold delay to 100 ms — verify ring appears faster
7. Change hold delay to 500 ms — verify ring requires longer hold
8. Close and reopen Mouser — verify settings persist

### M-4: Cross-Application Test

1. Open a browser, hold thumb button — verify ring appears over browser
2. Switch to Finder/Explorer, hold — verify ring appears over file manager
3. Verify the active application does NOT lose focus when ring appears
4. Verify clicking in the active application still works after ring dismisses

### M-5: Multi-Monitor Test

1. Move cursor to secondary monitor
2. Hold thumb button — verify ring appears at cursor on correct monitor
3. Verify ring is fully visible (screen edge clamping for edge cases)

### M-6: Stress Test

1. Rapidly press and release the thumb button 20 times
2. Verify no orphaned overlays, no crashes, no stuck states
3. Hold, release, quick press, hold, release in rapid succession
4. Verify correct behaviour throughout

---

## Coverage Goals

| Area | Target | Method |
|------|--------|--------|
| Sector geometry | 100% branch coverage | T-1 unit tests |
| Controller state machine | All transitions covered | T-2 unit tests |
| Controller thread safety | No races under stress | T-3 stress tests |
| Config migration | All paths | T-4 unit tests |
| Overlay lifecycle | Construction/show/hide | T-5 widget tests |
| Engine integration | All three modes | T-6 unit tests |
| Backend properties | Read/write round-trip | T-7 unit tests |
| End-to-end interaction | Happy path + edge cases | M-1 through M-6 manual |
