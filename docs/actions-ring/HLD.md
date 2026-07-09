# Actions Ring — High-Level Design

## 1. Overview

The Actions Ring is a radial quick-action overlay for the MX Master 4's
dedicated thumb button (CID 0x00C3). Pressing and holding the button displays a
configurable pie menu at the cursor; releasing over a sector executes that
action. A quick press (below the hold threshold) fires a single default action,
preserving backward compatibility with the current simple-button behaviour.

### 1.1 Goals

| # | Goal | Metric |
|---|------|--------|
| G1 | Reduce repetitive menu navigation | User reaches any mapped action in one hold + release |
| G2 | Eyes-free operation (Blind Mode) | Scroll-wheel sector cycling with haptic detents, no overlay |
| G3 | Zero latency perception | Overlay appears within one frame (~16 ms) of threshold |
| G4 | No dependency on external software | All logic runs inside Mouser — no cloud, no Options+ |
| G5 | Cross-platform parity | macOS, Windows, Linux — identical feature set |

### 1.2 Non-Goals (Phase 1)

- Per-sector icons / emoji rendering
- Nested sub-rings
- Modifier-shifted alternate action sets (Duolink-style)
- Plugin / marketplace system
- Ring size / appearance customisation UI

---

## 2. Architecture

### 2.1 Component Diagram

```
  ┌──────────────────────────────────────────────────────────────┐
  │  HID Layer (mouse_hook_base.py)                              │
  │  CID 0x00C3 → _on_hid_thumb_button_down/up()               │
  │       ↓ dispatch(ACTIONS_RING_DOWN / ACTIONS_RING_UP)       │
  └──────────────────────┬───────────────────────────────────────┘
                         │ hook thread
  ┌──────────────────────▼───────────────────────────────────────┐
  │  Engine (engine.py)                                          │
  │  _setup_hooks() routes actions_ring events to:              │
  │    Ring mode  → ActionsRingController.on_button_down/up()   │
  │    Simple mode → existing _make_handler()                    │
  │    Disabled   → no registration                              │
  └──────────────────────┬───────────────────────────────────────┘
                         │
  ┌──────────────────────▼───────────────────────────────────────┐
  │  ActionsRingController (core/actions_ring.py)         NEW    │
  │                                                              │
  │  State machine: IDLE → WAITING → ACTIVE → IDLE              │
  │  - on_button_down(): start hold timer                        │
  │  - on_button_up(): quick-press (timer pending) or resolve   │
  │  - _on_hold_triggered(): emit show signal, play haptic      │
  │  - resolve_sector(angle): sector math                        │
  │                                                              │
  │  Communicates via callbacks (set by Backend):                │
  │    show_ring_cb, hide_ring_cb, execute_action_cb,           │
  │    play_haptic_cb                                            │
  └──────────────────────┬───────────────────────────────────────┘
                         │ Qt signals (QueuedConnection)
  ┌──────────────────────▼───────────────────────────────────────┐
  │  Backend (ui/backend.py)                                     │
  │  New signals:                                                │
  │    _showRingRequest(int x, int y, list slots)               │
  │    _hideRingRequest()                                        │
  │  Handlers create/destroy the overlay on the Qt main thread.  │
  └──────────────────────┬───────────────────────────────────────┘
                         │
  ┌──────────────────────▼───────────────────────────────────────┐
  │  ActionsRingOverlay (ui/actions_ring_overlay.py)       NEW   │
  │                                                              │
  │  QWidget subclass — frameless, transparent, always-on-top.  │
  │  QPainter-drawn radial sectors with labels.                 │
  │  Internal QTimer (16 ms) polls QCursor.pos() for sector     │
  │  highlighting while visible.                                 │
  │  Emits: action_selected(int), cancelled()                   │
  └──────────────────────────────────────────────────────────────┘
```

### 2.2 New Files

| File | Purpose |
|------|---------|
| `core/actions_ring.py` | Controller state machine, sector geometry, hold timer |
| `ui/actions_ring_overlay.py` | QPainter-based radial overlay widget |
| `ui/qml/ActionsRingConfig.qml` | Configuration panel embedded in MousePage.qml |
| `tests/test_actions_ring.py` | Unit tests for controller and config migration |

### 2.3 Modified Files

| File | Changes |
|------|---------|
| `core/engine.py` | Route actions_ring events through controller; add controller lifecycle |
| `core/config.py` | Migration v17→v18; new settings and per-profile `actions_ring_slots` |
| `ui/backend.py` | New signals, overlay lifecycle, `actionsRingSlots` property |
| `ui/qml/MousePage.qml` | Conditional ActionsRingConfig panel for actions_ring button |
| `ui/locale_manager.py` | Localised strings for Actions Ring UI |

---

## 3. Interaction Model

### 3.1 Press Duration Discrimination

```
Button DOWN ──┐
              ├─ start threading.Timer(hold_threshold_s)
              │
              ├─ Button UP before timer fires?
              │    YES → cancel timer → execute quick-press action
              │    NO  → timer fires → enter ACTIVE state
              │
              ├─ [ACTIVE: ring visible / blind mode active]
              │    Cursor movement → sector tracking (overlay polls)
              │    Scroll events → sector cycling (blind mode)
              │
              └─ Button UP while ACTIVE
                   Sector >= 0 → execute that sector's action
                   Sector == -1 (dead zone / Esc) → cancel, no action
```

### 3.2 Hold Threshold

Default: **250 ms**. Configurable via `actions_ring_hold_ms` setting (range:
100–500 ms). Below typical intentional-hold time (~200 ms) but above accidental
touch. Sits above the gesture recogniser's settle timeout (90 ms) and haptic
dedup window (100 ms).

### 3.3 Three Operating Modes

| Mode | Quick Press | Hold | Config Key |
|------|------------|------|------------|
| **Ring** | Execute `actions_ring` mapping | Show overlay, select sector | `"ring"` |
| **Simple** | Execute `actions_ring` mapping | Same as quick press (no timer) | `"simple"` |
| **Disabled** | Nothing | Nothing | `"disabled"` |

---

## 4. Visual Design

### 4.1 Overlay Appearance

```
              ┌─────────────┐
              │  Screenshot  │
        ┌─────┤             ├─────┐
        │ Mute│             │Play/│
        │  🔇 │    [dead]   │Pause│
        ├─────┤    zone     ├─────┤
        │ Lock│             │Show │
        │  🔒 │             │Desk │
        └─────┤             ├─────┘
              │Mission Ctrl │
              └─────────────┘

  Outer radius : 110 px (220 px diameter)
  Dead zone    : 30 px radius (no-selection region)
  Sectors      : 4–8, each spanning 360/N degrees
  Sector 0     : centered at 12 o'clock (0 degrees = up)
```

### 4.2 Specifications

| Property | Value |
|----------|-------|
| Outer diameter | 220 px |
| Dead zone radius | 30 px |
| Slot count | 4–8 (default 4) |
| Position | Cursor at hold moment, clamped to screen edges |
| Dark background | `rgba(20, 20, 20, 0.85)` |
| Highlighted sector | `rgba(0, 212, 170, 0.30)` (Mouser accent) |
| Sector borders | `rgba(255, 255, 255, 0.15)`, 1 px |
| Label | System font, 11 px, white |
| Appear animation | 100 ms scale 0.85 → 1.0, ease-out |
| Dismiss | Immediate (no animation) |

### 4.3 Window Flags

```python
Qt.WindowType.FramelessWindowHint
| Qt.WindowType.WindowStaysOnTopHint
| Qt.WindowType.Tool                     # no taskbar entry
| Qt.WindowType.WindowDoesNotAcceptFocus # no focus steal
```

Plus `WA_TranslucentBackground` and `WA_ShowWithoutActivating`.

The overlay does NOT grab the mouse or keyboard. Cursor tracking is done by
polling `QCursor.pos()` on a 16 ms QTimer inside the overlay widget. This
avoids focus theft — the user's active application stays focused.

---

## 5. Haptic Integration

| Event | Waveform | ID | When |
|-------|----------|----|------|
| Ring activated | SHARP_STATE_CHANGE | 0 | Hold timer fires |
| Sector crossing | Button press | 1 | Cursor crosses sector boundary |
| Action executed | COMPLETED | 7 | Release on valid sector |
| Cancel | (none) | — | Release in dead zone |

Haptic pulses respect the existing `haptic_dedup` 100 ms window to prevent
rapid-fire during fast sweeps across multiple sectors.

---

## 6. Configuration Schema

### 6.1 New Settings (global)

```python
"actions_ring_mode": "ring"        # "ring" | "simple" | "disabled"
"actions_ring_hold_ms": 250        # hold threshold in milliseconds
```

### 6.2 New Per-Profile Data

```python
"actions_ring_slots": [            # ordered list of action IDs
    "screenshot_fullscreen",
    "play_pause",
    "show_desktop",
    "lock_screen",
]
```

The existing `"actions_ring": "none"` mapping is retained as the quick-press
action. `actions_ring_slots` defines the ring sectors. They are independent:
the quick-press action does not need to appear in the ring.

### 6.3 Migration v17 → v18

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

### 6.4 Backward Compatibility

- `actions_ring` mapping key unchanged — Simple mode and quick-press use it
- Profiles without `actions_ring_slots` get the default 4-slot list via migration
- Devices without Actions Ring button: no change (controller never instantiated)

---

## 7. Engine Integration

### 7.1 Controller Lifecycle

The `ActionsRingController` is created by the Engine at startup (or on
`reload_config()`) only when:
1. The connected device has `"actions_ring"` in its supported buttons
2. `actions_ring_mode` is `"ring"`

The controller holds no Qt dependencies directly — it communicates via
callbacks. The Backend wires these callbacks to Qt signals at init time.

### 7.2 Hook Registration (Ring Mode)

```python
# In Engine._setup_hooks(), for btn_key == "actions_ring":
if ring_mode == "ring":
    self.hook.register("actions_ring_down",
                       lambda e: self._ring.on_button_down())
    self.hook.register("actions_ring_up",
                       lambda e: self._ring.on_button_up())
    self.hook.block("actions_ring_down")
    self.hook.block("actions_ring_up")
```

### 7.3 Action Execution

The controller calls `execute_action(action_id)` (from `key_simulator`) for
the resolved sector. Engine-handled actions (`toggle_smart_shift`,
`switch_scroll_mode`, `cycle_dpi`, `cycle_desktops`) are routed through
a callback that the Engine provides, not called directly.

### 7.4 Per-App Profile Switching

Ring slots are stored per-profile in `actions_ring_slots`. The existing
`AppDetector` → `Engine._on_app_change()` → profile switch → `_setup_hooks()`
flow automatically reloads the controller with the new profile's slots.

---

## 8. Cross-Platform Considerations

| Concern | macOS | Windows | Linux |
|---------|-------|---------|-------|
| Overlay window | Tool + Frameless + StaysOnTop | Same | X11: same. Wayland: may need layer-shell. |
| Focus prevention | `WA_ShowWithoutActivating` | May need `WS_EX_NOACTIVATE` via `winId()` | EWMH `_NET_WM_STATE_SKIP_TASKBAR` |
| Cursor position | `QCursor.pos()` | Same | Same (X11). Wayland: may not work without compositor support. |
| DPI scaling | `devicePixelRatio()` for ring sizing | Same | Same |

**Wayland fallback:** If `QCursor.pos()` returns (0, 0) on Wayland, degrade
gracefully — center the ring on screen and log a warning. Blind mode works
regardless since it uses scroll-wheel cycling, not cursor position.

---

## 9. Phased Delivery

### Phase 1 — MVP

- `ActionsRingController` state machine (IDLE / WAITING / ACTIVE)
- Hold timer with configurable threshold
- Quick-press passthrough to existing single-action handler
- `ActionsRingOverlay` with QPainter rendering
- Sector math (angle → sector index, dead zone detection)
- Haptic on activation (waveform 0) and execution (waveform 7)
- Config migration v18
- Basic QML config panel (mode selector, quick-press action, slot list, hold delay)
- Engine integration
- Unit tests

### Phase 2 — Blind Mode and Polish

- Scroll-wheel sector cycling during ACTIVE state
- Haptic detents on sector advance (waveform 1), wrap-around (waveform 3)
- Persistent slot index between activations
- Sector-crossing haptic in visual mode
- Peek labels (brief text at cursor in blind mode)
- Screen-edge clamping
- Light-theme support
- Drag-to-reorder in config UI

### Phase 3 — Advanced

- Per-sector icons
- Modifier-shifted alternate action sets (Duolink-style)
- Nested sub-rings
- Ring position memory (pre-highlight last-used sector per profile)
- Accessibility (screen reader announcements)

---

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Overlay steals focus from active app | Unusable — user loses context | `WindowDoesNotAcceptFocus` + `WA_ShowWithoutActivating`; no mouse/keyboard grab |
| Hold timer races with quick press | Wrong action fired | Timer cancelled atomically in `on_button_up()`; `_state` checked before dispatch |
| Haptic dedup suppresses ring activation pulse | User doesn't know ring is active | Ring activation uses waveform 0 (different from any recent button haptic) |
| QPainter performance on large sector counts | Janky overlay | Max 8 sectors; QPainter draws < 1 ms for simple arcs |
| Wayland cursor position unavailable | Ring appears at wrong position | Fallback to screen center; blind mode unaffected |
| Config migration breaks existing configs | User loses settings | `setdefault()` only; no existing keys modified |
