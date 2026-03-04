from talon import Module, Context, actions, app, noise, registry

mod = Module()
mod.tag("noise_map_active", desc="Active when noise_map is enabled")

ctx = Context()
ctx_override = Context()
ctx_override.matches = "tag: user.noise_map_active"

CHANNEL = "noise_map"

_pop_registered = False
_hiss_registered = False


def _noise_pop(_):
    actions.user.input_map_channel_handle(CHANNEL, "pop")


def _noise_hiss(active):
    if active:
        actions.user.input_map_channel_handle(CHANNEL, "hiss")
    else:
        actions.user.input_map_channel_handle(CHANNEL, "hiss_stop")


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
    ctx.tags = ["user.noise_map_active"]


def _disable():
    global _pop_registered, _hiss_registered
    if _pop_registered:
        noise.unregister("pop", _noise_pop)
        _pop_registered = False
    if _hiss_registered:
        noise.unregister("hiss", _noise_hiss)
        _hiss_registered = False
    actions.user.input_map_channel_unregister(CHANNEL)
    ctx.tags = []


def _override_community_noise_handlers():
    """Suppress community pop/hiss handlers while noise_map is active.

    Community scripts (e.g. mouse click on pop, scroll on hiss) register
    their own noise actions. When noise_map is enabled, we override those
    actions with skip() in a tag-gated context so they don't conflict.
    When noise_map is disabled, the tag is cleared and the overrides
    no longer match, restoring normal community behavior automatically.
    """
    if registry.actions.get("user.noise_trigger_pop"):
        ctx_override.action("user.noise_trigger_pop")(lambda: actions.skip())
    if registry.actions.get("user.noise_trigger_hiss"):
        ctx_override.action("user.noise_trigger_hiss")(lambda active: actions.skip())
    if registry.actions.get("user.on_pop"):
        ctx_override.action("user.on_pop")(lambda: actions.skip())


app.register("ready", _override_community_noise_handlers)


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
