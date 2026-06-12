using System;
using System.ComponentModel;
using System.IO;
using System.Reflection;
using HarmonyLib;
using MultigridProjector.Utilities;
using MultigridProjectorDedicated;
using MultigridProjectorServer.MultigridProjector.Utilities;
using VRage.FileSystem;
using VRage.Plugins;
using ConfigStorage = PluginSdk.Config.ConfigStorage;

// Define assembly version when compiled by Magnetar
#if !DEV_BUILD
using System.Reflection;

[assembly: AssemblyVersion("0.9.2")]
[assembly: AssemblyFileVersion("0.9.2")]
#endif

namespace ServerPlugin;

// ReSharper disable once UnusedType.Global
public class Plugin : IPlugin
{
    public const string Name = "MultigridProjector";

    public static Plugin Instance { get; private set; }

    private static Harmony Harmony => new Harmony("com.spaceengineers.multigridprojector");

    public PluginConfig Config { get; private set; }
    private string configPath;
    private static readonly string ConfigFileName = "MultigridProjector.cfg";

    [System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.NoInlining)]
    public void Init(object gameInstance)
    {
        Instance = this;

        PluginLog.Logger = new PluginLogger();
        PluginLog.Info("Loading");

        try
        {
            configPath = Path.Combine(MyFileSystem.UserDataPath, ConfigFileName);
            Config = LoadConfig(configPath);
            Config.PropertyChanged += OnConfigPropertyChanged;

            // Expose the server configuration to shared code through the shared interface
            MultigridProjector.Config.PluginConfig.Current = Config;

            var isOldDotNetFramework = Environment.Version.Major < 5;
            if (isOldDotNetFramework && !WineDetector.IsRunningInWineOrProton())
            {
                try
                {
                    EnsureOriginal.VerifyAll();
                }
                catch (NotSupportedException e)
                {
                    PluginLog.Error(e, "Disabled the plugin due to potentially incompatible code changes in the game or plugin patch collisions. Please report the exception below on the SE Mods Discord (invite is on the Workshop page):");
                    return;
                }
            }

            Harmony.PatchAll(Assembly.GetExecutingAssembly());
        }
        catch (Exception e)
        {
            PluginLog.Error(e, "Failed to load");
            throw;
        }

        PluginLog.Info("Loaded");
    }

    public void Dispose()
    {
        try
        {
            if (Config != null)
            {
                Config.PropertyChanged -= OnConfigPropertyChanged;
                SaveConfig();
            }
        }
        catch (Exception e)
        {
            PluginLog.Error(e, "Dispose failed");
        }

        if (PluginLog.Logger != null)
        {
            PluginLog.Info("Unloaded");
            PluginLog.Logger = null;
        }

        Instance = null;
    }

    public void Update()
    {
    }

    private PluginConfig LoadConfig(string path)
    {
        try
        {
            var loaded = ConfigStorage.LoadXml<PluginConfig>(path);
            ConfigStorage.SaveXml(loaded, path);
            return loaded;
        }
        catch (Exception ex)
        {
            PluginLog.Error(ex, $"Failed to load configuration file: {path}");

            var config = new PluginConfig();
            try
            {
                ConfigStorage.SaveXml(config, path);
            }
            catch (Exception)
            {
                // Ignored
            }

            return config;
        }
    }

    private void SaveConfig()
    {
        if (Config != null && configPath != null)
            ConfigStorage.SaveXml(Config, configPath);
    }

    private void OnConfigPropertyChanged(object sender, PropertyChangedEventArgs e)
    {
        try
        {
            SaveConfig();
        }
        catch (Exception ex)
        {
            PluginLog.Error(ex, $"Failed to save configuration file: {configPath}");
        }
    }
}
