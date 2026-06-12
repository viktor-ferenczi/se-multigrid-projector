namespace MultigridProjector.Config
{
    // Holds the active configuration so shared code can read it without knowing whether it is
    // backed by the client settings dialog or the server PluginSdk configuration. The client and
    // server plugins assign Current during their initialization. Until then a safe default is used.
    public static class PluginConfig
    {
        public static IPluginConfig Current { get; set; } = new DefaultPluginConfig();
    }

    internal sealed class DefaultPluginConfig : IPluginConfig
    {
        public bool PreviewBlockVisuals => true;
    }
}
