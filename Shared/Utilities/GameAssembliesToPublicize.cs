using System.Runtime.CompilerServices;

// Keep these IgnoresAccessChecksTo entries in sync with the <Publicize> entries in
// ClientPlugin.csproj and ServerPlugin.csproj. Extra entries (e.g. Sandbox.Graphics is
// only publicized by the client) are harmless for assemblies that do not access them.
[assembly: IgnoresAccessChecksTo("Sandbox.Game")]
[assembly: IgnoresAccessChecksTo("SpaceEngineers.Game")]
[assembly: IgnoresAccessChecksTo("Sandbox.Graphics")]
