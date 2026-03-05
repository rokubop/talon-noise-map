import inspect
import re

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


def _noise_pop(_):
    actions.user.input_map_channel_handle(CHANNEL, "pop")


def _noise_hiss(active):
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

    skip_prefixes = ["user.noise_map"]
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
        return actions.user.input_map_channel_get_legend(CHANNEL, mode)

    def noise_map_reset():
        """Reset the noise_map by re-registering with a fresh map"""
        actions.user.input_map_channel_unregister(CHANNEL)
        noise_map = actions.user.noise_map()
        actions.user.input_map_channel_register(CHANNEL, noise_map)

    def noise_map_event_register(cb: callable):
        """Register an event callback for noise_map"""
        actions.user.input_map_channel_event_register(CHANNEL, cb)

    def noise_map_event_unregister(cb: callable):
        """Unregister an event callback for noise_map"""
        actions.user.input_map_channel_event_unregister(CHANNEL, cb)
