using System;
using System.Diagnostics;
using System.Linq;
using MultigridProjector.Config;
using MultigridProjector.Logic;
using Sandbox.Game.Multiplayer;
using Sandbox.Game.World;
using Sandbox.ModAPI;

// ReSharper disable once CheckNamespace
namespace MultigridProjector.Utilities
{
    public enum Role
    {
        SinglePlayer,
        MultiplayerServer,
        MultiplayerClient,
        DedicatedServer,
    }

    // MGP's traffic between the client and server plugins on mod channel Presence.Channel.
    //
    // A server (dedicated or a client hosting the game) sends every connected client a presence
    // packet with its version, a few seconds after the client joined and then at an interval.
    // A client starts in client-only mode, where it sends exactly what a vanilla client sends,
    // and switches to the full feature set (ServerHasPlugin) on the first presence packet of its
    // own major version. In full mode it sends its projector build requests as mod messages,
    // which the server checks and builds (BuildRequests).
    public class Comms : IDisposable
    {
        public static Role Role;
        public static bool ServerHasPlugin;

        // The version this plugin advertises and accepts, like "1.0.0"
        public static readonly string PluginVersion = GetPluginVersion();

        // MGP 0.9.x clients switch to full mode on any packet from the server on the legacy channel
        private static readonly byte[] LegacySignature = { 2, 3, 5, 7, 11, 13, 17, 19 };

        private static readonly Stopwatch Clock = Stopwatch.StartNew();
        private readonly PresenceSchedule schedule = new PresenceSchedule();
        private readonly byte[] presence;
        private bool loggedIgnoredPresence;
        private int frame;

        public Comms()
        {
            Role = DetectRole();

            // If we're in single player we already know we have MGP
            if (Role == Role.SinglePlayer)
            {
                ServerHasPlugin = true;
                return;
            }

            ServerHasPlugin = Role != Role.MultiplayerClient;

            // A test hook: the version a server advertises, to test clients of another major version
            var advertised =
                Environment.GetEnvironmentVariable("MGP_TEST_PRESENCE_VERSION") ?? PluginVersion;
            presence = Presence.EncodePresence(advertised);

            MyAPIGateway.Multiplayer.RegisterSecureMessageHandler(Presence.Channel, OnMessage);

            PluginLog.Info(
                $"Comms: {Role}, version {PluginVersion}"
                    + (
                        Role == Role.MultiplayerClient
                            ? ", client-only mode until the server's presence packet"
                            : $", advertising {advertised}"
                    )
            );
        }

        public void Dispose()
        {
            if (Role == Role.SinglePlayer)
                return;

            MyAPIGateway.Multiplayer.UnregisterSecureMessageHandler(Presence.Channel, OnMessage);
        }

        // Called on every simulation frame
        public void Update()
        {
            if (Role != Role.DedicatedServer && Role != Role.MultiplayerServer)
                return;

            // Once a second is plenty for a schedule counted in seconds
            if (++frame % 60 != 0)
                return;

            var config = PluginConfig.Current;
            var online = MySession.Static?.Players?.GetOnlinePlayers();
            if (online == null)
                return;

            var clients = online
                .Where(p => p.IsRealPlayer && p.Id.SerialId == 0 && p.Id.SteamId != Sync.MyId)
                .Select(p => p.Id.SteamId);

            foreach (
                var steamId in schedule.Due(
                    clients,
                    Clock.Elapsed.TotalSeconds,
                    config.PresenceDelaySeconds,
                    config.PresenceIntervalSeconds
                )
            )
            {
                MyAPIGateway.Multiplayer.SendMessageTo(Presence.Channel, presence, steamId);

                if (config.LegacyClientSupport)
                    MyAPIGateway.Multiplayer.SendMessageTo(
                        Presence.LegacyChannel,
                        LegacySignature,
                        steamId
                    );

                PluginLog.Debug($"Sent the presence packet to {steamId}");
            }
        }

        private void OnMessage(ushort channel, byte[] data, ulong sender, bool fromServer)
        {
            try
            {
                if (Role == Role.MultiplayerClient)
                {
                    if (fromServer)
                        OnPresence(data);
                    return;
                }

                // Only the server takes build requests, from its clients
                if (fromServer || sender == Sync.MyId)
                    return;

                if (!BuildRequest.TryDecode(data, out var request))
                {
                    PluginLog.Debug(
                        $"Ignored a malformed packet of {data?.Length ?? 0} bytes from {sender}"
                    );
                    return;
                }

                BuildRequests.Handle(sender, request);
            }
            catch (Exception e)
            {
                PluginLog.Error(e, $"Failed to handle a packet from {sender}");
            }
        }

        private void OnPresence(byte[] data)
        {
            if (Presence.IsCompatible(data, PluginVersion, out var serverVersion))
            {
                if (!ServerHasPlugin)
                    PluginLog.Info(
                        $"Server plugin present, version {serverVersion}: full feature set"
                    );

                ServerHasPlugin = true;
                return;
            }

            if (loggedIgnoredPresence)
                return;

            loggedIgnoredPresence = true;
            var shown = serverVersion ?? $"{data?.Length ?? 0} bytes that are not a version";
            PluginLog.Info(
                $"Ignored the server's presence packet ({shown}), it is not compatible with {PluginVersion}: client-only mode"
            );
        }

        public static void SendBuildRequest(BuildRequest request)
        {
            MyAPIGateway.Multiplayer.SendMessageToServer(Presence.Channel, request.Encode());
        }

        private static string GetPluginVersion()
        {
            var version = typeof(Comms).Assembly.GetName().Version;
            return $"{version.Major}.{version.Minor}.{Math.Max(0, version.Build)}";
        }

        private static Role DetectRole()
        {
            if (MyAPIGateway.Utilities.IsDedicated)
                return Role.DedicatedServer;

            if (MyAPIGateway.Multiplayer.MultiplayerActive)
                return MyAPIGateway.Multiplayer.IsServer
                    ? Role.MultiplayerServer
                    : Role.MultiplayerClient;

            return Role.SinglePlayer;
        }
    }
}
