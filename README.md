# Noise Map

![Version](https://img.shields.io/badge/version-0.1.0-blue)
![Status](https://img.shields.io/badge/status-experimental-orange)

Map Talon's built-in noises (pop/hiss) using the same [input_map](https://github.com/rokubop/talon-input-map/) API — with combos, modes, throttle, debounce, and more.

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
actions.user.noise_map_enable()   # Start routing noises through your map
actions.user.noise_map_disable()  # Restore default pop/hiss behavior
```

### Examples

#### Pop combos

```python
noise_map = {
    "pop":     ("click", lambda: actions.mouse_click(0)),        # single pop
    "pop pop": ("right click", lambda: actions.mouse_click(1)),  # double pop
}
```

Single pop is delayed by the combo window (~300ms) while waiting to see if a second pop follows. Use `:now` to execute immediately and still detect the combo — useful when the combo builds on the first action:

```python
noise_map = {
    "pop:now": ("aim", lambda: actions.user.aim_start()),    # fires immediately
    "pop pop": ("fire", lambda: actions.user.fire()),         # fires while already aiming
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

#### Hiss debounce

Prevent accidental hiss triggers (e.g. from speech containing "ss" sounds):

```python
noise_map = {
    "hiss:db_150":  ("run", lambda: actions.user.start_running()),  # only fires after 150ms of sustained hiss
    "hiss_stop":    ("", lambda: actions.user.stop_running()),
}
```

See [talon-input-map](https://github.com/rokubop/talon-input-map/) for the full feature set including conditions, modifiers, and more.

### Custom pop/hiss handlers

When enabled, noise_map automatically suppresses the community default pop/hiss actions (`noise_trigger_pop`, `noise_trigger_hiss`, `on_pop`) so they don't conflict. If you have additional custom pop/hiss actions, add them to `_override_community_noise_handlers` in `noise_map.py`:

```python
def _override_community_noise_handlers():
    ...
    # Add your custom action overrides here
    if registry.actions.get("user.my_custom_pop_action"):
        ctx_override.action("user.my_custom_pop_action")(lambda: actions.skip())
```

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

- [**talon-input-map**](https://github.com/rokubop/talon-input-map/) (v0.8.0+)

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
git clone <github_url>  # Add github URL to manifest.json
```

> **Note**: Review code from unfamiliar sources before installing.