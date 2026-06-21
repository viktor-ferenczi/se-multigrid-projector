// DO NOT USE A NAMESPACE HERE!
// CRITICAL: Magnetar (and Pulsar) locate this class via assembly.GetType("Preloader"),
// which only succeeds for a top-level type with no namespace.

// This plugin does no Cecil pre-patching, so it declares neither TargetDLLs nor a Patch
// method. Only the Finish() post-hook is used. Magnetar still runs the hook because
// HasPatches counts post-hooks (see Magnetar Shared/Preloader.cs).
//
// Finish() runs in SetupPlugins, before the game starts. At that point the game has not
// initialized yet, so we can install a Harmony hook on MyInitializer.InvokeBeforeRun. When it
// later runs (early in the dedicated server startup, after logging/filesystem are ready but
// before world-load compilation), the hook applies the plugin's patches. This matters because
// on the dedicated server IPlugin.Init runs only after the world has already loaded — far too
// late for the projector patches to take effect for grids built during world load.
// See ServerPlugin.Plugin.InstallEarlyBootstrap.
//
// ReSharper disable once UnusedType.Global
public class Preloader
{
    // ReSharper disable once UnusedMember.Global
    public static void Finish()
    {
        ServerPlugin.Plugin.InstallEarlyBootstrap();
    }
}
