using System.IO;
using System.Runtime.CompilerServices;
using System.Text.RegularExpressions;
using Xunit;

// The MGP API has a version of its own, apart from the plugin's. Agents embedded in mods and PB
// scripts turn themselves off unless it starts with "0." (SE-1274), so it stays on 0.x. The
// plugin and the shim must report the same one. Read from the sources: both need the game.
public class ApiVersionTests
{
    private static string Repo([CallerFilePath] string path = "") =>
        Path.GetFullPath(Path.Combine(Path.GetDirectoryName(path), "..", ".."));

    private static string VersionIn(string file)
    {
        var text = File.ReadAllText(Path.Combine(Repo(), file));
        var match = Regex.Match(text, "public string Version => \"([^\"]+)\";");
        Assert.True(match.Success, file);
        return match.Groups[1].Value;
    }

    [Fact]
    public void PluginAndShimReportTheSameApiVersion()
    {
        Assert.Equal(
            VersionIn("Shared/Logic/MultigridProjectorApiProvider.cs"),
            VersionIn("MultigridProjectorApi/Api/MultigridProjectorModShim.cs")
        );
    }

    [Fact]
    public void ApiVersionStaysOnZeroMajor()
    {
        Assert.StartsWith("0.", VersionIn("Shared/Logic/MultigridProjectorApiProvider.cs"));
    }
}
