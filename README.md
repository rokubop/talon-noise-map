# Talon Noise Map

![Version](https://img.shields.io/badge/version-0.5.0-blue)
![Status](https://img.shields.io/badge/status-experimental-orange)

Advanced remapping for your default Talon pop and hiss noises, using [talon-input-map](https://github.com/rokubop/talon-input-map/) - with combos, modes, throttle, debounce, and more.

## Usage

### 1. Override `noise_map()` to define your map

```python
ctx = Context()

noise_map = {
    "pop": ("jump", lambda: actions.user.gamekit_button_tap("a")),
    "hiss": ("dash", lambda: actions.user.gamekit_button_tap("x")),
    "hiss_stop": ("", lambda: None),
}

# With modes
noise_map = {
    "default": {
        "pop": ("jump", lambda: ...),
        "hiss": ("run", lambda: ...),
        "hiss_stop": ("", lambda: None),
    },
    "combat": {
        "pop": ("attack", lambda: ...),
        "hiss": ("block", lambda: ...),
        "hiss_stop": ("", lambda: ...),
    },
}

@ctx.action_class("user")
class Actions:
    def noise_map():
        return noise_map
```

### 2. Enable/disable

```python
actions.user.noise_map_enable()
actions.user.noise_map_disable()
```

### 3. Set mode

```python
actions.user.noise_map_mode_set("combat")
actions.user.noise_map_mode_set("default")
```

### Examples

#### Pop combos

```python
noise_map = {
    "pop":     ("click", lambda: actions.mouse_click(0)),        # single pop (delayed by combo window)
    "pop pop": ("right click", lambda: actions.mouse_click(1)),  # double pop
}
```

Single pop is delayed by the combo window (~300ms) while waiting to see if a second pop follows. Use `:now` to execute immediately and still detect the combo - useful when the combo builds on the first action:

```python
noise_map = {
    "pop:now": ("aim", lambda: actions.user.aim_start()),    # fires immediately
    "pop pop": ("fire", lambda: actions.user.fire()),        # fires while already aiming
}
```

#### After
Continued pops with eventual after conditions:

```python
noise_map = {
    "pop": ("hold jump", lambda: actions.user.jump_hold()),  # fires on first pop
    # Can continue pop pop pop...
    "pop:after_100": ("release jump", lambda: actions.user.jump_release()),  # fires 100ms after a pop, if no second pop occurs
}
```

#### Hiss duration

Trigger different actions based on how long hiss is held:

```python
noise_map = {
    "hiss":               ("", lambda: None),  # start event (required)
    "hiss_stop:dur<300":  ("tap", lambda: actions.user.dodge()),      # brief hiss
    "hiss_stop:dur>=300": ("hold", lambda: actions.user.charge()),    # sustained hiss
}
```

#### Hiss throttle

Rate-limit a continuous action while hissing:

```python
noise_map = {
    "hiss:th_90":  ("scroll", lambda: actions.user.scroll_down()),  # max once per 90ms
    "hiss_stop":   ("", lambda: None),
}
```

#### Hiss debounce start

Prevent accidental hiss triggers (e.g. from speech containing "ss" sounds):

```python
noise_map = {
    "hiss:db_150":  ("run", lambda: actions.user.start_running()),  # only fires after 150ms of sustained hiss
    "hiss_stop":    ("", lambda: actions.user.stop_running()),
}
```

#### Hiss debounce stop

Prevent accidental hiss triggers stops.

```python
noise_map = {
    "hiss":  ("jump", lambda: actions.user.hold_jump()),
    "hiss_stop:db_150":  ("", lambda: actions.user.jump_release()),
}
```

See [talon-input-map](https://github.com/rokubop/talon-input-map/) for the full feature set including conditions, modifiers, and more.

### Custom pop/hiss handlers

When enabled, `noise_map` automatically suppresses Talon's default pop/hiss behavior, and if applicable also suppresses `parrot(pop)`, `parrot(hiss)`, `noise(pop)`, `noise(hiss)`.


## Actions

| Action | Description |
|---|---|
| `noise_map()` | Override to return your map config |
| `noise_map_enable()` | Enable noise_map |
| `noise_map_disable()` | Disable noise_map |
| `noise_map_mode_set(mode)` | Set mode |
| `noise_map_mode_get()` | Get current mode |
| `noise_map_mode_cycle()` | Cycle to next mode |
| `noise_map_mode_revert()` | Revert to previous mode |
| `noise_map_get(mode?)` | Get map dict for a mode |
| `noise_map_get_legend(mode?)` | Get legend for a mode |
| `noise_map_reset()` | Re-register with fresh map |
| `noise_map_event_register(cb)` | Register event callback |
| `noise_map_event_unregister(cb)` | Unregister event callback |

## Installation

### Dependencies

- [**talon-input-map**](https://github.com/rokubop/talon-input-map/) (v1.0.0+)

### Install

Clone the dependencies and this repo into your [Talon](https://talonvoice.com/) user directory:

```sh
# Mac/Linux
cd ~/.talon/user

# Windows
cd ~/AppData/Roaming/talon/user

# Dependencies
git clone https://github.com/rokubop/talon-input-map/

# This repo
git clone https://github.com/rokubop/talon-noise-map
```