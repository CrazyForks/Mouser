# Actions Ring — Execution Plan

## Overview

Phase 1 MVP implementation, broken into work packages that can be developed
and tested independently. Each package lists the files touched, the
acceptance criteria, and dependencies on other packages.

---

## WP-1: Config Migration v17 → v18

**Files:** `core/config.py`, `tests/test_config.py`

**Changes:**
1. Bump `DEFAULT_CONFIG["version"]` from 17 to 18.
2. Add to `DEFAULT_CONFIG["settings"]`:
   - `"actions_ring_mode": "ring"` — operating mode
   - `"actions_ring_hold_ms": 250` — hold threshold
3. Add to `DEFAULT_CONFIG["profiles"]["default"]["mappings"]`:
   - `"actions_ring_slots": ["screenshot_fullscreen", "play_pause", "show_desktop", "lock_screen"]`
4. Add migration block in `_migrate()`:
   ```python
   if version < 18:
       s = cfg.setdefault("settings", {})
       s.setdefault("actions_ring_mode", "ring")
       s.setdefault("actions_ring_hold_ms", 250)
       for prof in cfg.get("profiles", {}).values():
           m = prof.get("mappings", {})
           m.setdefault("actions_ring_slots", [
               "screenshot_fullscreen", "play_pause",
               "show_desktop", "lock_screen",
           ])
       cfg["version"] = 18
   ```

**Tests:**
- Existing config tests pass with version assertion updated to 18
- New test: v17 config migrates to v18 with correct defaults
- New test: v18 config is not modified by migration
- New test: existing profiles gain `actions_ring_slots` without overwriting custom mappings

**Dependencies:** None — this is the foundation.

---

## WP-2: ActionsRingController

**Files:** `core/actions_ring.py` (new), `tests/test_actions_ring.py` (new)

**Class: `ActionsRingController`**

### State Machine

```
IDLE ──[on_button_down()]──→ WAITING ──[timer fires]──→ ACTIVE
  ↑                              │                          │
  │                              │ [on_button_up()]         │ [on_button_up()]
  │                              ↓                          ↓
  └────── quick-press action ────┘     resolve sector → execute / cancel
```

### Public API

```python
class ActionsRingController:
    IDLE = "idle"
    WAITING = "waiting"
    ACTIVE = "active"

    def __init__(self, slots, hold_ms, quick_action,
                 execute_cb, play_haptic_cb,
                 show_ring_cb, hide_ring_cb,
                 get_cursor_pos_cb):
        ...

    @property
    def state(self) -> str: ...

    def on_button_down(self) -> None:
        """Called from hook thread on ACTIONS_RING_DOWN."""

    def on_button_up(self) -> None:
        """Called from hook thread on ACTIONS_RING_UP."""

    def update_cursor_pos(self, x: int, y: int) -> int:
        """Compute sector from cursor position. Returns sector index or -1."""

    def resolve_sector_at(self, x: int, y: int) -> int:
        """Same as update_cursor_pos but intended for final resolution."""

    def shutdown(self) -> None:
        """Cancel any pending timer."""
```

### Sector Geometry

```python
@staticmethod
def angle_to_sector(dx: int, dy: int, num_sectors: int) -> int:
    """Map (dx, dy) offset from ring center to sector index.
    Returns -1 if inside dead zone (< 30 px from center).
    Sector 0 is centered at 12 o'clock."""
    dist = math.hypot(dx, dy)
    if dist < DEAD_ZONE_RADIUS:
        return -1
    angle = math.degrees(math.atan2(dx, -dy)) % 360
    sector_size = 360.0 / num_sectors
    return int((angle + sector_size / 2) % 360 / sector_size)
```

### Threading

- `on_button_down()` / `on_button_up()` are called from the hook thread.
- The hold timer runs on a `threading.Timer` daemon thread.
- `show_ring_cb` / `hide_ring_cb` are expected to be thread-safe (they emit
  Qt signals internally).
- The controller itself uses a `threading.Lock` to protect state transitions.

**Tests:** See TEST_PLAN.md sections T-1 through T-6.

**Dependencies:** None.

---

## WP-3: ActionsRingOverlay

**Files:** `ui/actions_ring_overlay.py` (new)

**Class: `ActionsRingOverlay(QWidget)`**

### Responsibilities

1. Render radial sectors using `QPainter` in `paintEvent()`.
2. Highlight the sector under the cursor via `QTimer`-based polling.
3. Manage appear/dismiss lifecycle.
4. Report selected sector back to the controller/backend.

### Key Design Decisions

- **No mouse grab.** The overlay is purely visual — cursor tracking is
  done by polling `QCursor.pos()`, not by receiving mouse events.
- **No keyboard grab.** Escape key handling is done by the controller
  (listening for an Escape keypress event via the hook or a global shortcut).
- **No focus steal.** `WindowDoesNotAcceptFocus` + `WA_ShowWithoutActivating`.
- **QPainter only.** No QGraphicsScene, no QML overlay — keep it simple.

### Rendering

For each sector `i` in `range(N)`:
1. Compute start angle and span: `start = 90 - i * (360/N) - (360/N)/2`
2. Build a `QPainterPath` arc from inner dead-zone radius to outer radius.
3. Fill with background color (or accent if highlighted).
4. Draw label text at the sector's midpoint angle, offset from center.

### Public API

```python
class ActionsRingOverlay(QWidget):
    action_selected = Signal(int)   # sector index
    cancelled = Signal()

    def show_ring(self, center_x, center_y, slot_labels, ring_diameter=220):
        """Position, configure, and show the overlay."""

    def hide_ring(self):
        """Hide the overlay."""

    def set_highlighted_sector(self, index: int):
        """Update which sector is visually highlighted. -1 = none."""

    @property
    def current_sector(self) -> int:
        """The sector currently under the cursor. -1 = dead zone."""
```

**Dependencies:** None (can be developed independently of WP-2).

---

## WP-4: Engine Integration

**Files:** `core/engine.py`, `ui/backend.py`

### Engine Changes

1. Import `ActionsRingController` from `core.actions_ring`.
2. In `__init__()`, create controller if device has actions_ring and mode is `"ring"`.
3. In `_setup_hooks()`, route `actions_ring_down/up` events:
   - Ring mode → `self._ring.on_button_down()` / `.on_button_up()`
   - Simple mode → existing `_make_handler(action_id, "actions_ring")`
   - Disabled → skip registration
4. Add `set_ring_show_callback()`, `set_ring_hide_callback()` for Backend wiring.
5. On `reload_config()` or profile switch: tear down old controller, create new one
   with updated slots from the new profile.

### Backend Changes

1. Add internal signals:
   ```python
   _showRingRequest = Signal(int, int, list)  # x, y, slot_labels
   _hideRingRequest = Signal()
   ```
2. Connect signals to handlers with `Qt.QueuedConnection`.
3. Handler `_handleShowRing()`: create `ActionsRingOverlay` if not exists,
   call `show_ring()`.
4. Handler `_handleHideRing()`: call `overlay.hide_ring()`.
5. Wire engine callbacks:
   ```python
   engine.set_ring_show_callback(self._onEngineShowRing)
   engine.set_ring_hide_callback(self._onEngineHideRing)
   ```
6. Add QML-visible properties:
   - `actionsRingMode` (read/write)
   - `actionsRingHoldMs` (read/write)
   - `actionsRingSlots` (read/write, list of action IDs)

### Action Execution Flow

When the overlay reports a selected sector:
1. Backend receives `action_selected(sector_index)` signal from overlay.
2. Backend looks up `actions_ring_slots[sector_index]` from config.
3. Backend calls `engine.execute_action(action_id)` (or the engine-handled
   action dispatch for special actions).
4. Haptic waveform 7 (COMPLETED) fires.

**Dependencies:** WP-1 (config), WP-2 (controller), WP-3 (overlay).

---

## WP-5: Configuration UI

**Files:** `ui/qml/ActionsRingConfig.qml` (new), `ui/qml/MousePage.qml`,
`ui/locale_manager.py`

### ActionsRingConfig.qml

Embedded in MousePage when the selected button is `actions_ring` and the
device has the button. Contains:

1. **Mode ComboBox:** Ring / Simple / Disabled
2. **Quick-Press Action ComboBox:** Reuses existing action picker delegate
3. **Slot List:** `ListView` with `model: actionsRingSlots`
   - Each row: drag handle + action ComboBox + remove button
   - "Add Slot" button (max 8 slots)
   - Minimum 2 slots enforced
4. **Hold Delay Slider:** Range 100–500 ms, step 10 ms

### MousePage.qml Changes

Add conditional loader below the existing action picker for the actions_ring
hotspot:
```qml
Loader {
    active: root.selectedButton === "actions_ring"
            && backend.deviceHasActionsRing
            && backend.actionsRingMode === "ring"
    sourceComponent: ActionsRingConfig { ... }
}
```

### Locale Manager

Add strings for all three locales (en, zh_CN, zh_TW):
- `actions_ring.mode_label`: "Mode"
- `actions_ring.mode_ring`: "Ring"
- `actions_ring.mode_simple`: "Simple"
- `actions_ring.mode_disabled`: "Disabled"
- `actions_ring.quick_press`: "Quick Press Action"
- `actions_ring.ring_slots`: "Ring Slots"
- `actions_ring.add_slot`: "Add Slot"
- `actions_ring.hold_delay`: "Hold Delay"
- `actions_ring.hold_delay_unit`: "ms"
- `actions_ring.max_slots`: "Maximum 8 slots"

**Dependencies:** WP-1 (config), WP-4 (backend properties).

---

## Implementation Order

```
WP-1 (Config) ─────────────────────────────┐
                                            ├──→ WP-4 (Engine) ──→ WP-5 (Config UI)
WP-2 (Controller) ─────────────────────────┤
                                            │
WP-3 (Overlay) ────────────────────────────┘

WP-1 and WP-2 can be developed in parallel.
WP-3 can be developed in parallel with WP-1 and WP-2.
WP-4 requires WP-1 + WP-2 + WP-3.
WP-5 requires WP-4.
```

### Parallel Agent Assignment

| Agent | Work Package | Notes |
|-------|-------------|-------|
| Agent A | WP-1 + WP-2 | Config migration + controller (tightly coupled) |
| Agent B | WP-3 | Overlay widget (independent, purely visual) |
| — | WP-4 | Integration — done after A and B complete |
| — | WP-5 | Config UI — done after WP-4 |

---

## Commit Strategy

One commit per work package, in dependency order:

1. `feat: Actions Ring config migration v18`
2. `feat: ActionsRingController state machine and sector geometry`
3. `feat: ActionsRingOverlay radial pie menu widget`
4. `feat: wire Actions Ring controller and overlay into engine and backend`
5. `feat: Actions Ring configuration UI in MousePage`

Each commit should pass all existing tests plus the new ones from that package.

---

## Definition of Done (Phase 1 MVP)

- [ ] Config migration v17 → v18 adds all new settings and per-profile slots
- [ ] Holding the actions ring button for > 250 ms shows a radial overlay at the cursor
- [ ] Quick press (< 250 ms) fires the mapped quick-press action
- [ ] Moving cursor to a sector highlights it
- [ ] Releasing on a sector executes that action
- [ ] Releasing in the dead zone cancels with no action
- [ ] Haptic fires on ring activation (waveform 0) and action execution (waveform 7)
- [ ] Simple mode bypasses the ring entirely
- [ ] Disabled mode ignores the button
- [ ] Config UI allows changing mode, quick-press action, ring slots, and hold delay
- [ ] All existing tests pass
- [ ] New tests for controller state machine, sector math, and config migration
- [ ] Cross-platform: overlay renders on macOS (primary), Windows, Linux
