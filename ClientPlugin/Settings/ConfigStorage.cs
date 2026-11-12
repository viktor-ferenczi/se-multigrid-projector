using System;
using System.IO;
using System.Xml.Serialization;
using VRage.FileSystem;
using VRage.Utils;

namespace ClientPlugin.Settings;

public static class ConfigStorage
{
    private static readonly string ConfigFileName = string.Concat(Plugin.Name, ".cfg");
    private static string ConfigFilePath => Path.Combine(MyFileSystem.UserDataPath, "Storage", ConfigFileName);

    public static void Save(Config config)
    {
        var path = ConfigFilePath;
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        using (var text = File.CreateText(path))
            new XmlSerializer(typeof(Config)).Serialize(text, config);
    }

    public static Config Load()
    {
        var path = ConfigFilePath;
        if (!File.Exists(path))
            return Config.Default;

        if (TryRead(path, new XmlSerializer(typeof(Config)), out var config))
            return config;

        // Before 0.9.2 the file held the same options under a ConfigObject root element. Reading
        // it failed and left every option at its default, Ship Welding on included (SE-1381).
        if (TryRead(path, new XmlSerializer(typeof(Config), new XmlRootAttribute("ConfigObject")), out config))
        {
            try
            {
                Save(config);
                MyLog.Default.WriteLineAndConsole($"{ConfigFileName}: Converted the config file of an old version: {path}");
            }
            catch (Exception e)
            {
                MyLog.Default.Warning($"{ConfigFileName}: Read the config file of an old version, but failed to convert it: {path}: {e.Message}");
            }

            return config;
        }

        MyLog.Default.Warning($"{ConfigFileName}: Failed to read the config file, all options are at their defaults: {path}");
        return Config.Default;
    }

    private static bool TryRead(string path, XmlSerializer serializer, out Config config)
    {
        try
        {
            using (var reader = File.OpenText(path))
                config = serializer.Deserialize(reader) as Config;
        }
        catch (Exception)
        {
            config = null;
        }

        return config != null;
    }
}