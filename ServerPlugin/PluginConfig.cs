using PluginSdk.Config;
using MultigridProjector.Config;

namespace ServerPlugin;

// Server-side configuration, declared and persisted through Magnetar's PluginSdk. Admins edit it
// remotely via Quasar, which renders the UI from these attributes. It implements the shared
// IPluginConfig so code in the Shared project can read it without knowing the backing mechanism.
public class PluginConfig : PluginSdk.Config.PluginConfig, IPluginConfig
{
    [BoolOption(
        "Let the plugin manage how the not-yet-built (preview) blocks of a multigrid projection look: " +
        "buildable blocks are shown as semi-transparent ghosts, blocks that cannot be built yet as holograms " +
        "(or hidden when the projector's \"Show only buildable\" option is on), already-built blocks are hidden, " +
        "and the projector's working sound and emissive (lit) state are driven accordingly. " +
        "Enabled by default. Turn it OFF only for compatibility with mods that set projector / preview-block " +
        "transparency themselves: when off, the plugin leaves all preview block visuals untouched.")]
    public bool PreviewBlockVisuals { get; set => SetField(ref field, value); } = true;
}
