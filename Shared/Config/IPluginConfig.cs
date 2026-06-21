namespace MultigridProjector.Config
{
    // Shared configuration interface used by code that runs on both the client and the server
    // (and therefore lives in the Shared project). The client implements this over the in-game
    // settings dialog (ClientPlugin/Config.cs), the server over Magnetar's PluginSdk
    // (ServerPlugin/PluginConfig.cs).
    public interface IPluginConfig
    {
        // Whether the plugin manages the appearance of the not-yet-built (preview) blocks of a
        // multigrid projection. When true:
        //   - buildable blocks are rendered as semi-transparent "ghost" blocks,
        //   - blocks that cannot be built yet are rendered as holograms (or hidden when the
        //     projector's "show only buildable" option is set),
        //   - blocks that are already built are hidden (the real block is shown instead),
        //   - the projector's working sound and emissive (lit) state are updated accordingly.
        // When false the plugin does not touch preview block visuals at all, leaving whatever the
        // game / other mods set (used for mod compatibility on the server).
        // Always true on the client; server-configurable via PluginSdk.
        bool PreviewBlockVisuals { get; }
    }
}
