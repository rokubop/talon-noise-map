import inspect
import re
from dataclasses import dataclass

from talon import Module, Context, actions, app, noise, registry

mod = Module()
mod.tag("noise_map_active", desc="Active when noise_map is enabled")

ctx = Context()
ctx_override = Context()
ctx_override.matches = "tag: user.noise_map_active"

CHANNEL = "noise_map"

_pop_registered = False
_hiss_registered = False
_saved_noise_callbacks = {}

# Phrase override state
_phrase_overrides = {}  # {"pop": "jump", "hiss": "forward"}

# Local event subscribers for phrase events
_event_subscribers = []


@dataclass
class _PhraseEvent:
    type: str
    mode: str
    input: str = ""
    label: str = ""


def _fire_event(event):
    """Fire an event to all registered noise_map event subscribers."""
    for cb in _event_subscribers:
        cb(event)


def _noise_pop(_):
    if "pop" in _phrase_overrides:
        phrase = _phrase_overrides["pop"]
        actions.mimic(phrase)
        _fire_event(_PhraseEvent(type="input", mode="phrase", input="pop", label=phrase))
        return
    actions.user.input_map_channel_handle(CHANNEL, "pop")


def _noise_hiss(active):
    if "hiss" in _phrase_overrides:
        if active:
            phrase = _phrase_overrides["hiss"]
            actions.mimic(phrase)
            _fire_event(_PhraseEvent(type="input", mode="phrase", input="hiss", label=phrase))
        return
    if active:
        actions.user.input_map_channel_handle(CHANNEL, "hiss")
    else:
        actions.user.input_map_channel_handle(CHANNEL, "hiss_stop")


def _suspend_noise_callbacks():
    """Unregister other pop/hiss noise.register() callbacks while noise_map is active."""
    _saved_noise_callbacks.clear()
    noise_dispatch = getattr(getattr(noise, "noise", None), "_dispatch_events", {})
    for topic in ("pop", "hiss"):
        for func, _rctx in list(noise_dispatch.get(topic, [])):
            if func not in (_noise_pop, _noise_hiss):
                _saved_noise_callbacks.setdefault(topic, []).append(func)
                noise.unregister(topic, func)
    if _saved_noise_callbacks:
        suspended = [f"{t}: {len(fns)}" for t, fns in _saved_noise_callbacks.items()]
        print(f"[noise_map] suspended noise callbacks: {', '.join(suspended)}")


def _restore_noise_callbacks():
    """Re-register previously suspended noise.register() callbacks."""
    for topic, funcs in _saved_noise_callbacks.items():
        for func in funcs:
            noise.register(topic, func)
    if _saved_noise_callbacks:
        print(f"[noise_map] restored noise callbacks")
    _saved_noise_callbacks.clear()


def _enable():
    global _pop_registered, _hiss_registered
    noise_map = actions.user.noise_map()
    actions.user.input_map_channel_register(CHANNEL, noise_map)
    if not _pop_registered:
        _pop_registered = True
        noise.register("pop", _noise_pop)
    if not _hiss_registered:
        _hiss_registered = True
        noise.register("hiss", _noise_hiss)
    _suspend_noise_callbacks()
    _override_pop_hiss_actions()
    ctx.tags = ["user.noise_map_active"]


def _disable():
    global _pop_registered, _hiss_registered
    if _pop_registered:
        noise.unregister("pop", _noise_pop)
        _pop_registered = False
    if _hiss_registered:
        noise.unregister("hiss", _noise_hiss)
        _hiss_registered = False
    _restore_noise_callbacks()
    actions.user.input_map_channel_unregister(CHANNEL)
    _phrase_overrides.clear()
    ctx.tags = []


_SKIP_FNS = {
    0: lambda: actions.skip(),
}


def _make_skip_fn(param_names: list[str]):
    """Create a skip function matching the expected parameter names."""
    if not param_names:
        return _SKIP_FNS[0]
    code = f"def skip_fn({', '.join(param_names)}): return actions.skip()"
    ns = {"actions": actions}
    exec(code, ns)
    return ns["skip_fn"]


def _try_override(action_name, action):
    """Try to override an action with skip(), auto-detecting the prototype signature."""
    for entry in (action if isinstance(action, list) else [action]):
        try:
            param_names = list(inspect.signature(entry).parameters.keys())
            ctx_override.action(action_name)(_make_skip_fn(param_names))
            return True
        except Exception:
            continue
    # Fallback: try 0 params then 1 param
    for param_names in [[], ["active"]]:
        try:
            ctx_override.action(action_name)(_make_skip_fn(param_names))
            return True
        except Exception:
            continue
    return False


def _find_bound_actions(*registries):
    """Find action names bound to pop/hiss from registry sources like
    registry.parrot_noises and registry.noises."""
    action_names = set()
    for reg in registries:
        for noise_name in ("pop", "hiss"):
            for impl in reg.get(noise_name, []):
                code = getattr(getattr(impl, "script", None), "code", None)
                if code:
                    for match in re.findall(r"(user\.\w+)\(", code):
                        action_names.add(match)
    return action_names


_overrides_applied = False


def _override_pop_hiss_actions():
    """Suppress pop/hiss actions while noise_map is active.

    Finds actions bound to parrot(pop)/parrot(hiss)/noise(pop)/noise(hiss)
    via the registry and overrides them with skip() in a tag-gated context
    so they don't conflict. When noise_map is disabled, the tag is cleared
    and the overrides no longer match, restoring normal behavior automatically.
    """
    global _overrides_applied
    if _overrides_applied:
        return
    _overrides_applied = True

    skip_prefixes = ["user.noise_map", "user.input_map"]
    bound_actions = _find_bound_actions(
        getattr(registry, "parrot_noises", {}),
        getattr(registry, "noises", {}),
    )
    target_actions = set()

    for action_name in bound_actions:
        if any(action_name.startswith(p) for p in skip_prefixes):
            continue
        if action_name in registry.actions:
            target_actions.add(action_name)

    overrides = []
    failures = []
    for action_name in sorted(target_actions):
        action = registry.actions[action_name]
        if _try_override(action_name, action):
            overrides.append(action_name)
        else:
            failures.append(action_name)
    if overrides:
        print(f"[noise_map] overriding {len(overrides)} actions: {', '.join(overrides)}")
    if failures:
        print(f"[noise_map] failed to override: {', '.join(failures)}")


# --- Actions ---


@mod.action_class
class Actions:
    def noise_map() -> dict:
        """Return the noise map configuration. Override in a context."""
        return {}

    def noise_map_enable():
        """Enable noise_map, registering noise callbacks and input_map channel"""
        _enable()

    def noise_map_disable():
        """Disable noise_map, unregistering noise callbacks and restoring defaults"""
        _disable()

    def noise_map_mode_set(mode: str):
        """Set the noise_map mode"""
        actions.user.input_map_channel_mode_set(CHANNEL, mode)

    def noise_map_mode_get() -> str:
        """Get the current noise_map mode"""
        if _phrase_overrides:
            return "phrase"
        return actions.user.input_map_channel_mode_get(CHANNEL)

    def noise_map_mode_cycle() -> str:
        """Cycle to the next noise_map mode"""
        return actions.user.input_map_channel_mode_cycle(CHANNEL)

    def noise_map_mode_revert() -> str:
        """Revert to the previous noise_map mode"""
        return actions.user.input_map_channel_mode_revert(CHANNEL)

    def noise_map_get(mode: str = None) -> dict:
        """Get the noise_map dict for a mode"""
        return actions.user.input_map_channel_get(CHANNEL, mode)

    def noise_map_get_legend(mode: str = None) -> dict:
        """Get the legend for the noise_map"""
        legend = actions.user.input_map_channel_get_legend(CHANNEL, mode)
        if _phrase_overrides and mode is None:
            for input_name, phrase in _phrase_overrides.items():
                legend[input_name] = phrase
        return legend

    def noise_map_reset():
        """Reset the noise_map by re-registering with a fresh map"""
        actions.user.input_map_channel_unregister(CHANNEL)
        noise_map = actions.user.noise_map()
        actions.user.input_map_channel_register(CHANNEL, noise_map)

    def noise_map_event_register(cb: callable):
        """Register an event callback for noise_map"""
        actions.user.input_map_channel_event_register(CHANNEL, cb)
        _event_subscribers.append(cb)

    def noise_map_event_unregister(cb: callable):
        """Unregister an event callback for noise_map"""
        actions.user.input_map_channel_event_unregister(CHANNEL, cb)
        try:
            _event_subscribers.remove(cb)
        except ValueError:
            for sub in _event_subscribers:
                if sub.__name__ == cb.__name__:
                    _event_subscribers.remove(sub)
                    break

    def noise_map_mode_phrase_set(input_name: str, phrase: str):
        """Set a phrase override for an input (pop or hiss), entering phrase mode.
        When the noise fires, it mimics the phrase instead of the configured action."""
        _phrase_overrides[input_name] = phrase
        _fire_event(_PhraseEvent(type="mode_change", mode="phrase"))

    def noise_map_mode_phrase_clear(input_name: str = ""):
        """Clear phrase override for an input, or all if empty.
        Reverts to the base noise_map mode when no overrides remain."""
        if input_name:
            _phrase_overrides.pop(input_name, None)
        else:
            _phrase_overrides.clear()
        if _phrase_overrides:
            _fire_event(_PhraseEvent(type="mode_change", mode="phrase"))
        else:
            current_mode = actions.user.input_map_channel_mode_get(CHANNEL)
            _fire_event(_PhraseEvent(type="mode_change", mode=current_mode))
